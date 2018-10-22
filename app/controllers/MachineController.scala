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
import play.api.data.FormError
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
import play.api.data.format.Formats.parsing
import play.api.data.format.Formatter
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.i18n.I18nSupport
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
 * == MAC-Addresses ==
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
      FormID.name       -> text,
      FormID.macAddress -> text.verifying(
                              error = "MAC address has invalid format.",
                              constraint = _.matches(macAddressRegexString)
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

  /** Form is used to add a new machine. */
  private[this] val modifyMachineForm = Form(
    mapping(
      FormID.id         -> optional(number),
      FormID.name       -> text,
      FormID.macAddress -> text.verifying(
        error = "MAC address has an invalid format. Only numbers and lowercase letters a to f are allowed.",
        constraint = _.matches(macAddressRegexString)
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
        FormID.id         -> machine.id.get.toString,
        FormID.name       -> machine.name,
        FormID.macAddress -> machine.macAddress,
        FormID.comment    -> machine.comment.getOrElse(""),
        FormID.isActive   -> machine.isActive.toString
      ))
      Ok(modify_machine(form))
    }
  }

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

  def addButtonsJs: EssentialAction = Action {
    Ok(views.js.javascript.add_buttons()).as(JAVASCRIPT)
  }

  private[this] val configureMachineForm: Form[ConfigureMachineData] = {
    import controllers.MachineController.FormWeek.weekdayFormatter

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
        "machineID" -> number,
        "runtimer" -> optional(longNumber),
        "weekdays" -> list(formWeek),
        "start"    -> list(optional(localTime("HH:mm"))),
        "end"      -> list(optional(localTime("HH:mm"))),
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
        machineID = id,
        runtimer  = config.headOption.map(_.runtimer),
        weekdays  = formWeeks.toList,
        starts    = starts.toList,
        ends      = ends.toList
      )

      val form = configureMachineForm.fill(conMachData)
      Ok(configure_machine(machine, form))
    }
  }

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
        val configActions = formData.runtimer.fold(DBIO.seq(
            machineConfigTable.filter(_.machineId === formData.machineID).delete,
        )) { runtimer =>
          DBIO.seq(
            machineConfigTable.filter(_.machineId === formData.machineID).delete,
            machineConfigTable += MachineConfig(formData.machineID, runtimer)
          )
        }
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

    implicit def weekdayFormatter: Formatter[Weekday] = new Formatter[Weekday] {
      override val format: Option[(String, Seq[Any])] = Some(("format.weekday", Seq.empty))
      override def bind(key: String, data: Map[String, String]): Either[Seq[FormError], Weekday] = {
        parsing(incoming => Weekday.week.find(day => day.toString == incoming).get, "error.weekday", Seq.empty)(key, data)
      }
      override def unbind(key: String, value: Weekday): Map[String, String] = {
        Map(key -> value.toString)
      }
    }
  }

  case class ConfigureMachineData(
    machineID: Int,
    runtimer: Option[Long],
    weekdays: List[FormWeek],
    starts: List[Option[LocalTime]],
    ends: List[Option[LocalTime]],
  )

  object FormID {
    val id = "id"
    val name = "name"
    val macAddress = "macAddress"
    val comment = "comment"
    val isActive = "isActive"
  }
}
