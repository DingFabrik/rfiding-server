package controllers

import controllers.PersonController.FormID
import controllers.PersonController.PersonFormData
import controllers.PersonController.SimplifiedPerson
import controllers.security.Security
import javax.inject.Inject
import javax.inject.Singleton
import models.Person
import play.api.Logger
import play.api.data.Form
import play.api.data.Forms.boolean
import play.api.data.Forms.email
import play.api.data.Forms.default
import play.api.data.Forms.mapping
import play.api.data.Forms.number
import play.api.data.Forms.optional
import play.api.data.Forms.text
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.i18n.I18nSupport
import play.api.libs.json.Json
import play.api.libs.json.Writes
import play.api.mvc.AbstractController
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesActionBuilder
import play.api.mvc.MessagesControllerComponents
import slick.jdbc.JdbcProfile
import slick.jdbc.SQLiteProfile.api._
import utils.database.TableProvider
import utils.navigation.NavigationComponent
import views.html.add_person
import views.html.list_persons
import views.html.modify_person

import scala.concurrent.ExecutionContext
import scala.concurrent.Future

//noinspection MutatorLikeMethodIsParameterless
@Singleton
class PersonController @Inject()(
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
  with Security {
  controller =>

  /** Form for managing a Persons details. */
  private[this] val personDetailsForm = Form(
    mapping(
      FormID.id       -> optional(number),
      FormID.memberId -> optional(number),
      FormID.fullName -> text,
      FormID.email    -> optional(email),
      // TODO: Apply play.api.data.Mapping.transform to isActive
      // Example boolean transformation:
      // boolean.transform(if (_) "true" else "false", _ == "true")
      // number.transform(_ == 1, if (_) 1 else 0)
      FormID.isActive   -> default(boolean, true)
    )(PersonFormData.apply)(PersonFormData.unapply)
  )

  /** Returns all persons in the database. */
  def listPersons: EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    db.run(personTable.result).map { persons =>
      Ok(list_persons(persons))
    }
  }

  /** Shows the add person form. */
  def addPerson: EssentialAction = isAuthenticated { implicit user => implicit request =>
    Ok(add_person(personDetailsForm))
  }

  /** Retrieves the person data and writes it to the database. */
  def addPersonPost: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    Logger.debug(request.toString())
    personDetailsForm.bindFromRequest.fold(
      formWithErrors => {
        Logger.debug(s"Something is wrong: $formWithErrors")
        Future.successful(BadRequest(add_person(formWithErrors)))
      },
      addUserData => {
        val newPerson = Person(
          id       = None,
          memberId = addUserData.memberId.map(_.toString),
          name     = addUserData.name,
          email    = addUserData.email,
          isActive = addUserData.isActive
        )
        db.run((personTable returning personTable.map(_.id)) += newPerson).map { insertId =>
          Redirect(routes.PersonController.listPersons()).flashing(FlashKey.PersonAdded -> insertId.toString)
        }
      }
    )
  }

  def modifyPerson(personId: Int): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
      val findPersonQuery = personTable.filter(_.id === personId)
      val tokenForPersonQuery = tokenTable.filter(_.ownerId === personId)
      val queries = findPersonQuery.result zip tokenForPersonQuery.result
      db.run(queries).map {
        //case Some(person, token)) =>
        case (Seq(person: Person), token) =>
          Logger.debug(s"person => $person")
          Logger.debug(s"token  => $token")
          val form = personDetailsForm.bind(Map(
            FormID.id       -> person.id.get.toString,
            FormID.memberId -> person.memberId.getOrElse(""),
            FormID.fullName -> person.name,
            FormID.email    -> person.email.getOrElse(""),
            FormID.isActive -> person.isActive.toString
          ))
          Ok(modify_person(form, token))
        case other =>
          Ok(s"$other")
        //Redirect(routes.PersonController.listPersons()).flashing("error" -> "Person not found")
      }
  }

  def modifyPersonPost: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    personDetailsForm.bindFromRequest.fold(
      formWithErrors => {
        Future.successful(BadRequest(modify_person(formWithErrors, Seq.empty)))
      },
      modifyPersonData => {
        val updatePerson = Person(
          id       = modifyPersonData.id,
          memberId = modifyPersonData.memberId.map(_.toString),
          name     = modifyPersonData.name,
          email    = modifyPersonData.email,
          isActive = modifyPersonData.isActive
        )
        val updateQuery = personTable.filter(_.id === updatePerson.id).update(updatePerson)
        db.run(updateQuery).map { _ =>
          Redirect(routes.PersonController.listPersons()).flashing(FlashKey.PersonUpdated -> modifyPersonData.id.get.toString)
        }
      }
    )
  }

  /** Implicit writer for a SimplifiedPerson instance. Needed by Json.toJson. */
  implicit val simplifiedPersonWrites: Writes[SimplifiedPerson] = Json.writes[SimplifiedPerson]

  /**
   * Looks up a string in the person table.
   *
   * @return The result is returned as a JSON object. jQuery's autocomplete widget requires the JSON data to consist of
   *         a list of JSON-objects containing two key-value pairs. The keys must be named "label" and "value".
   *         "label" is used for the name and "value" contains the database ID. Although this could be handled on the
   *         client side, we enforce this server-side by using the 'SimplifiedPerson' data object, which results in a
   *         much more compact and easier to write code than in the client-side javascript.
   */
  def findPerson(term: Option[String]): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    term.fold(Future.successful(Ok(""))) { needle: String =>
      val query = personTable.filter(_.name like s"%$needle%").take(5)
      db.run(query.result).map { persons: Seq[Person] =>
        val mappedPersons = persons.map(SimplifiedPerson(_))
        Ok(Json.toJson(mappedPersons))
      }
    }
  }

  def deletePerson(id: Int, returnTo: String): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val deletePersonQuery = personTable.filter(_.id === id).delete
    db.run(deletePersonQuery).map { _ =>
      val backRoute = returnTo match {
        case "persons" => routes.PersonController.listPersons()
        case _         => routes.TokenController.listTokens()
      }
      Redirect(backRoute).flashing(FlashKey.DeletedPerson -> id.toString)
    }
  }
}

object PersonController {

  case class PersonFormData(
    id: Option[Int],
    memberId: Option[Int],
    name: String,
    email: Option[String],
    isActive: Boolean
  )

  /** IDs used by forms. */
  object FormID {
    val id       = "id"
    val memberId = "memberId"
    val fullName = "fullName"
    val email    = "email"
    val isActive = "isActive"
  }

  /** Simple data holder to return specific person data used by a javascript autocomplete function. */
  case class SimplifiedPerson(label: String, value: String)
  object SimplifiedPerson {
    def apply(person: Person): SimplifiedPerson = {
      new SimplifiedPerson(label = person.name, value = person.id.fold("")(_.toString))
    }
  }
}
