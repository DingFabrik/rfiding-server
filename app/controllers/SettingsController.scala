package controllers

import controllers.security.PasswordUtil
import controllers.security.Security
import javax.inject.Inject
import javax.inject.Singleton
import models.User
import play.api.Logger
import play.api.data.Form
import play.api.data.Forms.email
import play.api.data.Forms.mapping
import play.api.data.Forms.optional
import play.api.data.Forms.text
import play.api.data.validation.Constraint
import play.api.data.validation.Invalid
import play.api.data.validation.Valid
import play.api.data.validation.ValidationError
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
import views.html.add_user
import views.html.list_users
import views.html.user_profile

import scala.concurrent.ExecutionContext
import scala.concurrent.Future


@Singleton
class SettingsController @Inject()(
  protected val dbConfigProvider: DatabaseConfigProvider,
  messagesAction: MessagesActionBuilder,
  mc: MessagesControllerComponents,
  passwordUtil: PasswordUtil
)(
  implicit ec: ExecutionContext,
  navigation: NavigationComponent,
) extends AbstractController(mc)
  with I18nSupport
  with HasDatabaseConfigProvider[JdbcProfile]
  with TableProvider
  with Security { controller =>
  import SettingsController.AddUserFormData
  import SettingsController.FormID
  import SettingsController.ModifyUserFormData

  private[this] val logger: Logger = Logger("api")

  /** The minimum length for passwords. */
  // TODO: Make this a configuration setting.
  private[this] val minPasswordLength = 6

  /** Constraint to check that password has a minimum length and the confirmation is valid. */
  private[this] val modifyUserCheckPasswordEquality: Constraint[ModifyUserFormData] = {
    Constraint("constraints.passwordcheck")({
      case ModifyUserFormData(_, _, Some(a), _) if a.length < minPasswordLength =>
        Invalid(Seq(ValidationError("error.password.minlength")))
      case ModifyUserFormData(_, _, a, b) if a != b =>
        Invalid(Seq(ValidationError("error.password.match")))
      case _ =>
        Valid
    })
  }

  /** Form for managing a Persons details. */
  private[this] val modifyUserForm = Form(
    mapping(
      FormID.userName            -> text,
      FormID.userMail            -> email,
      FormID.userPassword        -> optional(text),
      FormID.userPasswordConfirm -> optional(text),
    )(ModifyUserFormData.apply)(ModifyUserFormData.unapply).verifying(modifyUserCheckPasswordEquality)
  )

  /** Display the User profile form. */
  def userProfile: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    val query = userTable.filter(_.id === user.userID)
    db.run(query.result).map {
      case Seq(dbUser: User) =>
        val form = modifyUserForm.bind(Map(
          FormID.userName -> dbUser.name,
          FormID.userMail -> dbUser.email
        ))
        Ok(user_profile(form))
    }
  }

  /** Check and modify user data. */
  def userProfilePost: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    modifyUserForm.bindFromRequest.fold(
      formWithErrors => {
        logger.debug(s"Sending back $formWithErrors")
        Future.successful(BadRequest(user_profile(formWithErrors)))
      },
      modifyUserData => {
        val filteredTable = userTable.filter(_.id === user.userID)
        val updateQuery = modifyUserData.userPassword match {
          case Some(newPassword) =>
            filteredTable.map(u => (u.name, u.email, u.hash))
              .update((modifyUserData.userName, modifyUserData.userMail, passwordUtil.hash(newPassword)))
          case _ =>
            filteredTable.map(u => (u.name, u.email))
              .update((modifyUserData.userName, modifyUserData.userMail))
        }
        db.run(updateQuery).map { _ =>
          Redirect(routes.SettingsController.userProfile).flashing(FlashKey.UserProfileUpdated -> "")
        }
      }
    )
  }

  def listUsers: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    db.run(userTable.result).map { users: Seq[User] =>
      Ok(list_users(users))
    }
  }

  /** Constraint to check that password has a minimum length and the confirmation is valid. */
  private[this] val addUserCheckPasswordEquality: Constraint[AddUserFormData] = Constraint("constraints.passwordcheck")({
    case AddUserFormData(_, _, pw1, _) if pw1.isEmpty =>
      Invalid(Seq(ValidationError("error.password.empty")))
    case AddUserFormData(_, _, pw1, _) if pw1.length < minPasswordLength =>
      Invalid(Seq(ValidationError("error.password.minlength")))
    case AddUserFormData(_, _, pw1, pw2) if pw1 != pw2 =>
      Invalid(Seq(ValidationError("error.password.match")))
    case _ =>
      Valid
  })

  /** Form for managing a Persons details. */
  private[this] val addUserForm = Form(
    mapping(
      FormID.userName            -> text,
      FormID.userMail            -> email,
      FormID.userPassword        -> text,
      FormID.userPasswordConfirm -> text,
    )(AddUserFormData.apply)(AddUserFormData.unapply).verifying(addUserCheckPasswordEquality)
  )

  def addUser: EssentialAction = isAuthenticated { implicit user => implicit request =>
    Ok(add_user(addUserForm))
  }

  /** Check and modify user data. */
  def addUserPost: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    addUserForm.bindFromRequest.fold(
      formWithErrors => {
        logger.debug(s"Sending back $formWithErrors")
        Future.successful(BadRequest(add_user(formWithErrors)))
      },
      addUserData => {
        val query = (userTable returning userTable.map(_.id)) += User(
          id    = None,
          name  = addUserData.userName,
          email = addUserData.userMail,
          hash  = passwordUtil.hash(addUserData.userPassword)
        )
        db.run(query).map { newUserId: Int =>
          Redirect(routes.SettingsController.listUsers).flashing(FlashKey.UserAdded -> newUserId.toString)
        }
      }
    )
  }

  /** Show some details about this application. */
  def about: EssentialAction = isAuthenticated { implicit user => implicit request =>
    Ok(views.html.about())
  }
}

object SettingsController {
  case class ModifyUserFormData(
    userName: String,
    userMail: String,
    userPassword: Option[String],
    userPasswordConfirm: Option[String]
  )

  case class AddUserFormData(
    userName: String,
    userMail: String,
    userPassword: String,
    userPasswordConfirm: String
  )

  object FormID {
    val userMail = "userMail"
    val userName = "userName"
    val userPassword = "userPassword"
    val userPasswordConfirm = "userPasswordConfirm"
  }
}
