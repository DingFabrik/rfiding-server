package controllers

import java.time.Clock
import java.time.Duration
import java.time.LocalDateTime
import java.time.LocalTime

import controllers.ApiController.AccessDeniedException
import controllers.ApiController.AccessGrantedResult
import controllers.ApiController.MachineConfigResult
import controllers.ApiController.MachineNotFound
import controllers.ApiController.PossibleMachine
import controllers.ApiController.TokenStringInvalid
import controllers.ApiController.ValidToken
import controllers.ApiController.formatMachineString
import controllers.ApiController.formatTokenSeq
import controllers.security.Security
import javax.inject.Inject
import javax.inject.Singleton
import models.Machine
import models.MachineTime
import models.Person
import models.Token
import models.UnknownToken
import play.api.Logger
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.http.ContentTypes.JSON
import play.api.i18n.I18nSupport
import play.api.libs.json.Json
import play.api.libs.json.Writes
import play.api.mvc.AbstractController
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesActionBuilder
import play.api.mvc.MessagesControllerComponents
import play.api.mvc.Result
import play.api.mvc.Results
import slick.jdbc.JdbcProfile
import slick.jdbc.SQLiteProfile.api._
import utils.CustomIsomorphisms.seqByteIsomorphism
import utils.database.TableProvider
import utils.navigation.NavigationComponent

import scala.concurrent.ExecutionContext
import scala.concurrent.Future

@Singleton
class ApiController @Inject()(
  protected val dbConfigProvider: DatabaseConfigProvider,
  messagesAction: MessagesActionBuilder,
  mc: MessagesControllerComponents
)(
  implicit ec: ExecutionContext,
  navigation: NavigationComponent,
) extends AbstractController(mc)
  with I18nSupport
  with HasDatabaseConfigProvider[JdbcProfile]
  with TableProvider
  with Security { controller =>

  private[this] val logger: Logger = Logger("api")

  /** Implicit writer for a SimplifiedPerson instance. Needed by Json.toJson. */
  implicit private[this] val machineConfigWrites: Writes[MachineConfigResult] = Json.writes[MachineConfigResult]
  /** Implicit writer for a AccessGrantedResult instance. Needed by Json.toJson. */
  implicit private[this] val accessGrantedWrites: Writes[AccessGrantedResult] = Json.writes[AccessGrantedResult]

  /** Check if the given MachineTime is in a valid interval and matches the todays day of week. */
  private[this] def isTimeValid(times: MachineTime): Boolean = {
    val today = LocalDateTime.now().getDayOfWeek
    val now = LocalTime.now()
    times.weekdays.map(_.toDayOfWeek).contains(today) &&
      now.compareTo(times.startTime) >= 0 && now.compareTo(times.endTime) <= 0
  }

  /**
   * Calculates the remaining working period for a given machine time.
   *
   * This shouldn't be called if the end time is before now.
   * In case this is done anyway, 0 is returned and an appropriate log message is thrown.
   */
  private[this] def remainingWorkingPeriod(times: MachineTime): Long = {
    val now = LocalTime.now()
    val remaining = Duration.between(now, times.endTime).toMinutes * 60L
    if (remaining < 0) {
      logger.error(s"Got a negative remaining time for $times. This shouldn't happen.")
      0L
    } else {
      remaining
    }
  }

  /* **************************************************************************************************************** */

  def getMachineConfig(machine: String
  ): EssentialAction = Action.async {
    val formattedMachine = formatMachineString(machine)
    logger.info(s"Searching for machine config for machine $formattedMachine")

    val configQuery = machineTable.filter(_.macAddress === formattedMachine).joinLeft(machineConfigTable).on {
      case (machines, machineConfig) => machines.id === machineConfig.machineId
    }

    db.run(configQuery.result).map {
      case Seq((_, config)) =>
        Ok(Json.toJson(MachineConfigResult(
          runtimer         = config.flatMap(_.runtimer),
          minPower         = config.flatMap(_.minPower),
          controlParameter = config.flatMap(_.controlParameter)
        ))).as(JSON)
      case _ =>
        MachineNotFound.status
    }
  }

  /* **************************************************************************************************************** */
  /** Checks whether the given parameter is valid. */
  private[this] def hasValidTokenString(token: String)(invalid: Future[Result])(valid: Future[Result]): Future[Result] = {
    parameterCheck[String, Future[Result]](isParamValid = _.toLowerCase.matches(TokenRegexString))(token)(invalid)(valid)
  }

  private[this] def rememberUnknownToken(serial: Seq[Byte], machineId: Int): Unit = {
    val insertQuery = unknownTokenTable += UnknownToken(
      serial    = serial,
      machineId = machineId,
      readStamp = LocalDateTime.now(Clock.systemUTC())
    )
    db.run(insertQuery)
  }

  def checkMachineAccess(machineString: String, tokenUid: String
  ): EssentialAction = Action.async { hasValidTokenString(tokenUid) {
    Future.successful(TokenStringInvalid.status)
  } {
    val formattedMachine = formatMachineString(machineString)
    val uuid = formatTokenSeq(tokenUid)

    def machineTimesFut = {
      val machineQuery = machineTable.filter(_.macAddress === formattedMachine).joinLeft(machineTimesTable).on {
        case (machines, times) => machines.id === times.machineId
      }
      db.run(machineQuery.result)
    }

    def tokenQueryFut: Future[Seq[(Token, Option[Person])]] = {
      val tokenQuery = tokenTable.filter(_.serial === uuid).joinLeft(personTable).on {
        case (token, person) => token.ownerId === person.id
      }
      db.run(tokenQuery.result)
    }

    def checkQualificationFut(owner: Person, inputMachine: Machine) = {
      logger.debug(s"Checking ${owner.name} against ${inputMachine.name}")
      // TODO: Optimize query (use machine directly instead of joining it)
      val query = machineTable.filter(_.id === inputMachine.id.get).joinLeft(qualificationTable.filter(_.personId === owner.id)).on {
        case (machine, qualification) => machine.id === qualification.machineId
      }.map {
        case (_, qualiOpt) => qualiOpt
      }
      db.run(query.result)
    }

    def fail(reason: String): Nothing = {
      logger.debug(reason)
      throw new AccessDeniedException(reason)
    }

    val f1: Future[PossibleMachine] = machineTimesFut.map {
      case Seq() =>
        fail("Machine not found.")
      case (machineResult, _) +: _ if !machineResult.isActive =>
        fail(s"Machine '${machineResult.name}' restricted.")
      case results =>
        logger.debug("Machine with possible working periods found")
        val remainingOpt: Option[Long] = results.collectFirst {
          case (_, Some(time)) if isTimeValid(time) => remainingWorkingPeriod(time)
        }
        val (machine: Machine, _) = results.head
        PossibleMachine(machine, remainingOpt)
    }
    val f2: Future[ValidToken] = f1.flatMap { case PossibleMachine(machine, remainingOpt) => tokenQueryFut.map {
      case Seq((token, Some(owner))) if !token.isActive =>
        fail(s"Token for ${owner.name} restricted.")
      case Seq((_, Some(owner))) if !owner.isActive =>
        fail(s"Owner (${owner.name}) restricted.")
      case Seq((_, Some(owner))) =>
        logger.debug(s"Token found. It belongs to ${owner.name}.")
        ValidToken(owner, machine, remainingOpt)
      case Seq((_, None)) =>
        fail("Token without owner found. Token probably not removed from DB.")
      case _ =>
        rememberUnknownToken(uuid, machine.id.get)
        fail("Token not found.")
    }}
    val f3: Future[AccessGrantedResult] = f2.flatMap {
      case ValidToken(owner, machine, remainingOpt) => checkQualificationFut(owner, machine).map {
        case Seq(Some(_)) =>
          logger.debug(s"Quali OK.")
          AccessGrantedResult(access = 1, remainingOpt.getOrElse(0L))
        case _ =>
          fail(s"'${owner.name}' has no qualification for '${machine.name}'.")
      }
    }
    val f4 = f3.recover { case _: AccessDeniedException =>
      AccessGrantedResult(access = 0)
    }
    f4.map { result =>
      Ok(Json.toJson(result)).as(JSON)
    }
  }}

  /* **************************************************************************************************************** */

  def machineStatus(machine: String): EssentialAction = Action {
    val formattedMachine = formatMachineString(machine)
    logger.info(s"Retrieving machine status for machine $formattedMachine")
    val stuff: Seq[String] = Seq("to be implemented")
    Ok(Json.toJson(stuff)).as(JSON)
  }
}

object ApiController {

  /** Creates a MAC address divided by colons from a string already containing the MAC address out of hex chars. */
  def formatMachineString(machineBytes: String): String = {
    machineBytes.toLowerCase.grouped(2).mkString(":")
  }

  def formatTokenSeq(serialString: String): Seq[Byte] = {
    serialString.toLowerCase.grouped(2).map(Integer.parseInt(_, 16).toByte).toSeq
  }

  trait ApiStatus {
    def code: Int = 400
    def msg: String
    def status: Result = Results.Status(code)(Json.toJson(msg)).as(JSON)
  }
  object MachineNotFound extends ApiStatus {
    val msg: String = "Machine not found."
  }
  object NoConfigFound extends ApiStatus {
    val msg: String = "No config found."
  }
  object TokenStringInvalid extends ApiStatus {
    val msg: String = "Tokenstring invalid."
  }

  // TODO: Check if this can be merged with models.MachineConfig !!
  case class MachineConfigResult(
    runtimer: Option[Long],
    minPower: Option[Long],
    controlParameter: Option[String]
  )

  case class AccessGrantedResult(
    access: Int,
    workingtime: Long = 0L
  )

  trait AccessResult
  case class ValidToken(owner: Person, machine: Machine, workingtimeOpt: Option[Long]) extends AccessResult
  case class PossibleMachine(machine: Machine, workingtimeOpt: Option[Long]) extends AccessResult

  class AccessDeniedException(reason: String) extends RuntimeException
}
