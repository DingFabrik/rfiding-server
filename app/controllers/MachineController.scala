package controllers

import java.time.LocalTime

import controllers.MachineController.AddMachineData
import controllers.MachineController.ConfigureMachineData
import controllers.MachineController.FormID
import controllers.MachineController.FormWeek
import controllers.MachineController.ModifyMachineData
import controllers.security.Security
import javax.inject.Inject
import javax.inject.Singleton
import models.Machine
import models.MachineConfig
import models.MachineTime
import play.api.Logger
import play.api.data.Form
import play.api.data.Forms.boolean
import play.api.data.Forms.list
import play.api.data.Forms.localTime
import play.api.data.Forms.longNumber
import play.api.data.Forms.mapping
import play.api.data.Forms.number
import play.api.data.Forms.of
import play.api.data.Forms.optional
import play.api.data.Forms.text
import play.api.data.Mapping
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.i18n.I18nSupport
import play.api.libs.json.JsArray
import play.api.libs.json.JsObject
import play.api.libs.json.JsString
import play.api.libs.json.JsSuccess
import play.api.libs.json.Json.toJson
import play.api.mvc.AbstractController
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesActionBuilder
import play.api.mvc.MessagesControllerComponents
import slick.jdbc.JdbcProfile
import slick.jdbc.SQLiteProfile.api._
import utils.database.TableProvider
import utils.navigation.NavigationComponent
import utils.time.Weekday
import utils.time.Weekday.Friday
import utils.time.Weekday.Monday
import utils.time.Weekday.Saturday
import utils.time.Weekday.Sunday
import utils.time.Weekday.Thursday
import utils.time.Weekday.Tuesday
import utils.time.Weekday.Wednesday
import views.html.add_machine
import views.html.configure_machine
import views.html.list_machines
import views.html.modify_machine

import scala.concurrent.ExecutionContext
import scala.concurrent.Future

//noinspection MutatorLikeMethodIsParameterless
@Singleton
/**
 * Actions related to machines.
 *
 * == Format of MAC-Addresses ==
 * An MAC may look like ac:bc:32:b9:3f:13
 * Six hex values from 00 to ff, separated by colons.
 */
class MachineController @Inject()(
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

  /** Show a list of known machines. */
  def listMachines: EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    db.run(machineTable.result).map { machines: Seq[Machine] =>
      Ok(list_machines(machines))
    }
  }

  /** Form is used to add a new machine. */
  private[this] val addMachineForm = Form(
    mapping(
      FormID.machineName       -> text,
      FormID.macAddress -> text.verifying(
                              error = "MAC address has invalid format.",
                              constraint = _.matches(MacAddressRegexString)
      ),
      FormID.comment    -> optional(text),
      FormID.isActive   -> boolean,
    )(AddMachineData.apply)(AddMachineData.unapply)
  )

  /** Display add machine form. */
  def addMachine: EssentialAction = isAuthenticated { implicit user => implicit request =>
    Ok(add_machine(addMachineForm))
  }

  /** Evaluate form data for adding new machines. */
  def addMachinePost: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    addMachineForm.bindFromRequest.fold(
      formWithErrors => {
        Logger.debug(s"Something is wrong: $formWithErrors")
        Future.successful(BadRequest(add_machine(formWithErrors)))
      },
      addMachineData => {
        val newMachine = Machine(
          id         = None,
          name       = addMachineData.name,
          macAddress = addMachineData.macAddress,
          isActive   = addMachineData.isActive,
          comment    = addMachineData.comment
        )
        db.run((machineTable returning machineTable.map(_.id)) += newMachine).map { insertId =>
          Redirect(routes.MachineController.listMachines()).flashing("newMachines" -> insertId.toString)
        }
      }
    )
  }

  /** Deletes a machine from database. Machine times and configuration will also be deleted. */
  def deleteMachine(machineId: Int): EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    val deleteQuery = DBIO.seq(
      machineTimesTable.filter(_.machineId === machineId).delete,
      machineConfigTable.filter(_.machineId === machineId).delete,
      machineTable.filter(_.id === machineId).delete,
    ).transactionally
    db.run(deleteQuery).map { _ =>
      Redirect(routes.MachineController.listMachines()).flashing(FlashKey.DeletedMachine -> machineId.toString)
    }
  }

  /** Form is used to add a new machine. */
  private[this] val modifyMachineForm = Form(
    mapping(
      FormID.machineId         -> optional(number),
      FormID.machineName       -> text,
      FormID.macAddress -> text.verifying(
        error = "MAC address has an invalid format. Only numbers and lowercase letters a to f are allowed.",
        constraint = _.matches(MacAddressRegexString)
      ),
      FormID.comment    -> optional(text),
      FormID.isActive   -> boolean,
    )(ModifyMachineData.apply)(ModifyMachineData.unapply)
  )

  /** Modify existing machines. */
  def modifyMachine(id: Int): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val findMachineQuery = machineTable.filter(_.id === id)
    db.run(findMachineQuery.result).map { case Seq(machine) =>
      val form = modifyMachineForm.bind(Map(
        FormID.machineId   -> machine.id.get.toString,
        FormID.machineName -> machine.name,
        FormID.macAddress  -> machine.macAddress,
        FormID.comment     -> machine.comment.getOrElse(""),
        FormID.isActive    -> machine.isActive.toString
      ))
      Ok(modify_machine(form))
    }
  }

  /** Modify existing machines. Endpoint for form post. */
  def modifyMachinePost: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    modifyMachineForm.bindFromRequest.fold(
      formWithErrors => {
        Future.successful(BadRequest(modify_machine(formWithErrors)))
      },
      modifyMachineData => {
        val updateMachine = Machine(
          id         = modifyMachineData.id,
          name       = modifyMachineData.name,
          macAddress = modifyMachineData.macAddress,
          comment    = modifyMachineData.comment,
          isActive   = modifyMachineData.isActive
        )
        val updateQuery = machineTable.filter(_.id === updateMachine.id).update(updateMachine)
        db.run(updateQuery).map { _ =>
          Redirect(routes.MachineController.listMachines()).flashing(FlashKey.MachineUpdated -> modifyMachineData.id.get.toString)
        }
      }
    )
  }

  /** Method is called via javascript and toggles activation state of a token. */
  def toggleMachineActivePost(): EssentialAction =  isAuthenticatedAsync { implicit userId => implicit request =>
    request.body.asJson.map { jsValue =>
      ((jsValue \ "id").validate[Int], (jsValue \ "checked").validate[Boolean])
    } match {
      case Some((machineIdValue: JsSuccess[Int], checkedValue: JsSuccess[Boolean])) =>
        val query = machineTable.filter(_.id === machineIdValue.get).map(_.isActive).update(checkedValue.get)
        db.run(query).map { _ => Ok(toJson("")) }
      case _ =>
        Future.successful(BadRequest(toJson("")))
    }
  }

  /** Form is used to enter configuration for a machine. */
  private[this] val configureMachineForm: Form[ConfigureMachineData] = {
    import utils.forms.weekdayFormatter

    def formWeek: Mapping[FormWeek] = mapping(
      Monday.toString    -> optional(of[Weekday]),
      Tuesday.toString   -> optional(of[Weekday]),
      Wednesday.toString -> optional(of[Weekday]),
      Thursday.toString  -> optional(of[Weekday]),
      Friday.toString    -> optional(of[Weekday]),
      Saturday.toString  -> optional(of[Weekday]),
      Sunday.toString    -> optional(of[Weekday])
    )(FormWeek.apply)(FormWeek.unapply)

    Form(
      mapping = mapping(
        "machineID"        -> number,
        "runtimer"         -> optional(longNumber),
        "minPower"         -> optional(longNumber),
        "controlParameter" -> optional(text),
        "weekdays"         -> list(formWeek),
        "start"            -> list(optional(localTime("HH:mm"))),
        "end"              -> list(optional(localTime("HH:mm"))),
      )(ConfigureMachineData.apply)(ConfigureMachineData.unapply)
    )
  }

  /** Modify machine config. */
  def configureMachine(id: Int): EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    val machineQueryF = db.run(machineTable.filter(_.id === id).result)
    val timesQueryF   = db.run(machineTimesTable.filter(_.machineId === id).result)
    val configQueryF  = db.run(machineConfigTable.filter(_.machineId === id).result)

    machineQueryF.zip(timesQueryF).zip(configQueryF).map { case ((Seq(machine), times: Seq[MachineTime]), config: Seq[MachineConfig]) =>
      val (formWeeks, starts, ends) = times.map { machineTime =>
        (FormWeek(machineTime.weekdays), Some(machineTime.startTime), Some(machineTime.endTime))
      }.unzip3

      val conMachData = ConfigureMachineData(
        machineID        = id,
        runtimer         = config.headOption.flatMap(_.runtimer),
        minPower         = config.headOption.flatMap(_.minPower),
        controlParameter = config.headOption.flatMap(_.controlParameter),
        weekdays         = formWeeks.toList,
        starts           = starts.toList,
        ends             = ends.toList
      )

      val form = configureMachineForm.fill(conMachData)
      Ok(configure_machine(machine, form))
    }
  }

  /** Modify machine config. Form post endpoint. */
  def configureMachinePost: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    Logger.debug(s"request = $request")
    Logger.debug(s"request.body = ${request.body}")
    configureMachineForm.bindFromRequest.fold(
      formWithErrors => {
        Logger.debug(s"formWithErrors = $formWithErrors")
        val machineID = formWithErrors.apply("machineID").value.get.toInt
        db.run(machineTable.filter(_.id === machineID).result).map { case Seq(machine) =>
          BadRequest(configure_machine(machine, formWithErrors))
        }
      },
      formData => {
        val times: Seq[MachineTime] = (formData.weekdays, formData.starts, formData.ends).zipped.toSeq.collect {
          case (weekdays, Some(start), Some(end)) if weekdays.isSet =>
            MachineTime(None, formData.machineID, weekdays.toWeekdaySeq, start, end)
        }
        val configActions = DBIO.seq(
          machineConfigTable.filter(_.machineId === formData.machineID).delete,
          machineConfigTable += MachineConfig(
            machineId        = formData.machineID,
            runtimer         = formData.runtimer,
            minPower         = formData.minPower,
            controlParameter = formData.controlParameter
          )
        ).transactionally
        val actions = DBIO.seq(
          machineTimesTable.filter(_.machineId === formData.machineID).delete,
          machineTimesTable ++= times
        ).transactionally
        db.run(configActions).zip(db.run(actions)).map { _ =>
          Redirect(routes.MachineController.listMachines()).flashing(FlashKey.MachineTimesUpdated -> "OK")
        }
      }
    )
  }


  /**
   * Looks up a string in the machine table.
   *
   * @return The result is returned as a JSON object. jQuery's autocomplete widget requires the JSON data to consist of
   *         a list of JSON-objects containing two key-value pairs. The keys must be named "label" and "value".
   *         "label" is used for the name and "value" contains the database ID. Although this could be handled on the
   *         client side, we enforce this server-side by using the 'SimplifiedPerson' data object, which results in a
   *         much more compact and easier to write code than in the client-side javascript.
   */
  def findMachine(term: Option[String]): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    term.fold(Future.successful(Ok(""))) { needle: String =>
      val query = machineTable.filter(_.name like s"%$needle%").take(5)
      db.run(query.result).map { machines: Seq[Machine] =>
        val mj: Seq[JsObject] = machines.map { machine =>
          JsObject(Seq(
            "label" -> JsString(machine.name),
            "value" -> JsString(machine.id.get.toString)
          ))
        }
        val jsonMachines = JsArray(mj)
        Ok(jsonMachines).as(JSON)
      }
    }
  }

  /**
   * Looks up a string in the machine table.
   *
   * @return The result is returned as a JSON object. jQuery's autocomplete widget requires the JSON data to consist of
   *         a list of JSON-objects containing two key-value pairs. The keys must be named "label" and "value".
   *         "label" is used for the name and "value" contains the database ID. Although this could be handled on the
   *         client side, we enforce this server-side by using the 'SimplifiedPerson' data object, which results in a
   *         much more compact and easier to write code than in the client-side javascript.
   */
  def findQualificableMachine(user: Int, term: Option[String]): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    term.fold(Future.successful(Ok(""))) { needle: String =>
      val query = machineTable.filter(_.name like s"%$needle%").joinLeft(qualificationTable.filter(_.personId === user)).on {
        case (machine, qualification) => machine.id === qualification.machineId
      }.filterNot {
        case (_, qualificationColumn) => qualificationColumn.map(_.machineId).isDefined
      }.map {
        case (machine, _) => machine
      }

      db.run(query.result).map { machines: Seq[Machine] =>
        val jsonMachines: Seq[JsObject] = machines.map { machine =>
          Logger.debug(s"Machine = $machine")
          JsObject(Seq(
            "label" -> JsString(machine.name),
            "value" -> JsString(machine.id.get.toString)
          ))
        }
        Ok(JsArray(jsonMachines)).as(JSON)
      }
    }
  }


}

object MachineController {
  case class AddMachineData(
    name: String,
    macAddress: String,
    comment: Option[String],
    isActive: Boolean
  )

  case class ModifyMachineData(
    id: Option[Int],
    name: String,
    macAddress: String,
    comment: Option[String],
    isActive: Boolean
  )

  case class FormWeek(
    mo: Option[Weekday],
    tu: Option[Weekday],
    we: Option[Weekday],
    th: Option[Weekday],
    fr: Option[Weekday],
    sa: Option[Weekday],
    su: Option[Weekday]
  ) {
    private[this] val all = Seq(mo, tu, we, th, fr, sa, su)
    def isSet: Boolean = {
      all.exists(_.isDefined)
    }

    def toWeekdaySeq: Seq[Weekday] = {
      all.flatten
    }
  }

  object FormWeek {
    def apply(seq: Seq[Weekday]): FormWeek = {
      new FormWeek(
        mo = seq.find(_ == Monday),
        tu = seq.find(_ == Tuesday),
        we = seq.find(_ == Wednesday),
        th = seq.find(_ == Thursday),
        fr = seq.find(_ == Friday),
        sa = seq.find(_ == Saturday),
        su = seq.find(_ == Sunday)
      )
    }
  }

  case class ConfigureMachineData(
    machineID: Int,
    runtimer: Option[Long],
    minPower: Option[Long],
    controlParameter: Option[String],
    weekdays: List[FormWeek],
    starts: List[Option[LocalTime]],
    ends: List[Option[LocalTime]],
  )

  object FormID {
    val machineId   = "machineId"
    val machineName = "machineName"
    val macAddress  = "macAddress"
    val comment     = "comment"
    val isActive    = "isActive"
  }
}
