package controllers

import java.time.Clock
import java.time.Duration
import java.time.LocalDateTime
import java.time.LocalTime

import controllers.ApiController.MachineConfigResult
import controllers.ApiController.ResultExtender
import controllers.ApiController._
import controllers.security.Security
import io.swagger.annotations.Api
import io.swagger.annotations.ApiModelProperty
import io.swagger.annotations.ApiOperation
import io.swagger.annotations.ApiParam
import io.swagger.annotations.ApiResponse
import io.swagger.annotations.ApiResponses
import javax.inject.Inject
import javax.inject.Singleton
import models.MachineTime
import models.UnknownToken
import play.api.Logger
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.http.ContentTypes.JSON
import play.api.i18n.I18nSupport
import play.api.libs.json.JsValue
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
@Api
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

  /** Convenience method to return an AccessGrantedResult as JSON. */
  private[this] def JsonOK(result: AccessGrantedResult): Result = Ok(Json.toJson(result)).as(JSON)

  /* **************************************************************************************************************** */

  @ApiOperation(
    value = "Get Machine Configuration",
    notes = "Returns the configuration parameters for a machine.",
    response = classOf[MachineConfigResult]
  )
  @ApiResponses(Array(
    new ApiResponse(code = 400, message = "Machine not found."),
    new ApiResponse(code = 401, message = "No value for runtimer found."),
  ))
  def getMachineConfig(
    @ApiParam(value = "MAC address of machine to fetch. Numbers, lowercase letters from a to f and colons are allowed.",
      required = true,
      example = "ac:bc:32:b9:3f:13"
    ) machine: String
  ): EssentialAction = Action.async {
    val formattedMachine = formatMachineString(machine)
    logger.info(s"Searching for machine config for machine $formattedMachine")

    val configQuery = machineTable.filter(_.macAddress === formattedMachine).joinLeft(machineConfigTable).on {
      case (machines, machineConfig) => machines.id === machineConfig.machineId
    }

    db.run(configQuery.result).map {
      case Seq((_, Some(config))) => Ok(Json.toJson(MachineConfigResult(config.runtimer))).as(JSON)
      case Seq((_, None))         => NoRuntimerFound.status
      case _                      => MachineNotFound.status
    }
  }

  /* **************************************************************************************************************** */
  /** Checks whether the given parameter is valid. */
  private[this] def hasValidTokenString(token: String)(invalid: Future[Result])(valid: Future[Result]): Future[Result] = {
    parameterCheck[String, Future[Result]](isParamValid = _.matches("([0-9a-fA-F]{8})"))(token)(invalid)(valid)
  }

  private[this] def rememberUnknownToken(serial: Seq[Byte], machineId: Int): Unit = {
    val insertQuery = unknownTokenTable += UnknownToken(
      serial    = serial,
      machineId = machineId,
      readStamp = LocalDateTime.now(Clock.systemUTC())
    )
    db.run(insertQuery)
  }

  @ApiOperation(
    value = "Check machine access rights",
    notes = """Check if access to a machine is allowed.
Access will be denied if owner, token or machine is set to inactive.
Access will further be denied if token is not found or the current time is not in a valid interval or the
day of week does not match to the todays one."""
  )
  @ApiResponses(Array(
    new ApiResponse(code = 400, message = "Machine not found."),
    new ApiResponse(code = 400, message = "Tokenstring invalid."),
  ))
  def checkMachineAccess(
    @ApiParam(
      value = "MAC address of machine to fetch. Numbers, lowercase letters from a to f and colons are allowed.",
      required = true,
      example = "acbc32b93f13"
    ) machineString: String,
    @ApiParam(
      value = "UID of token to verify. Numbers and lowercase letters from a to f are allowed. Exactly 8 chars.",
      required = true,
      example = "42A65C22"
    ) tokenUid: String
  ): EssentialAction = Action.async { hasValidTokenString(tokenUid) {
    TokenStringInvalid.status.fut
  } {
    val formattedMachine = formatMachineString(machineString)
    logger.info(s"Checking machine access for machine $formattedMachine and token $tokenUid")

    val machineQuery = machineTable.filter(_.macAddress === formattedMachine).joinLeft(machineTimesTable).on {
      case (machines, times) => machines.id === times.machineId
    }

    val uuid = formatTokenSeq(tokenUid)
    val tokenQuery = tokenTable.filter(_.serial === uuid).joinLeft(personTable).on {
      case (token, person) => token.ownerId === person.id
    }

    val tokenQueryFuture = db.run(tokenQuery.result)

    // We handle more cases then necessary to get more debug information.
    db.run(machineQuery.result).map {
      case Seq() =>
        logger.debug("Machine not found.")
        JsonOK(AccessGrantedResult(access = 0)).fut
      case (machineResult, _) +: _ if !machineResult.isActive =>
        logger.debug(s"Machine '${machineResult.name}' restricted.")
        JsonOK(AccessGrantedResult(access = 0)).fut
      case results =>
        logger.debug("Machine with possible working periods found")

        val remaining: Option[Long] = results.collectFirst {
          case (_, Some(time)) if isTimeValid(time) => remainingWorkingPeriod(time)
        }
        val machineId: Int = results.collectFirst { case (machineResult, _) => machineResult.id.get }.get

        tokenQueryFuture.map {
          case Seq((token, Some(owner))) if !token.isActive =>
            logger.debug(s"Token for ${owner.name} restricted.")
            val x: JsValue =Json.toJson(AccessGrantedResult(access = 0))
            JsonOK(AccessGrantedResult(access = 0))
          case Seq((_, Some(owner))) if !owner.isActive =>
            logger.debug(s"Owner (${owner.name}) restricted.")
            JsonOK(AccessGrantedResult(access = 0))
          case Seq((_, Some(owner))) =>
            logger.debug(s"Token found. It belongs to ${owner.name}.")
            JsonOK(AccessGrantedResult(access = 1, workingtime = remaining.getOrElse(0L)))
          case Seq((_, None)) =>
            logger.error("Token without owner found. Token probably not removed from DB.")
            JsonOK(AccessGrantedResult(access = 0))
          case _ =>
            logger.debug("Token not found.")
            rememberUnknownToken(uuid, machineId)
            JsonOK(AccessGrantedResult(access = 0))
        }
    }.flatten
  }}

  /* **************************************************************************************************************** */

  @ApiOperation(
    value = "Transmit machine status",
    notes = "Endpoint is used to transmit the actual machine status."
  )
  def machineStatus(
    @ApiParam(value = "MAC address of machine.", required = true,
      allowableValues = "Numbers, lowercase letters from a to f and colons.", example = "ac:bc:32:b9:3f:13")
    machine: String): EssentialAction = Action {
    val formattedMachine = formatMachineString(machine)
    logger.info(s"Retrieving machine status for machine $formattedMachine")
    val stuff: Seq[String] = Seq("to be implemented")
    Ok(Json.toJson(stuff)).as(JSON)
  }
}

object ApiController {

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
  object NoRuntimerFound extends ApiStatus {
    val msg: String = "No value for runtimer found."
  }
  object TokenStringInvalid extends ApiStatus {
    val msg: String = "Tokenstring invalid."
  }

  case class MachineConfigResult(
    @ApiModelProperty(value = "Maximum time of the Idle run timer. Unit: Seconds.")
    runtimer: Long
  )

  case class AccessGrantedResult(
    access: Int,
    workingtime: Long = 0L
  )

  implicit class ResultExtender(val underlying: Result) extends AnyVal {
    def fut: Future[Result] = Future.successful(underlying)
  }
}
