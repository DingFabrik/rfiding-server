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
  import SettingsController.FormID
  import SettingsController.UserFormData

  /** The minimum length for passwords. */
  // TODO: Make this a configuration setting.
  private[this] val minPasswordLength = 6

  /** Constraint to check that password has a minimum length and the confirmation is valid. */
  private[this] val checkPasswordEquality: Constraint[UserFormData] = Constraint("constraints.passwordcheck")({
    case UserFormData(_, Some(a), _) if a.length < minPasswordLength =>
      Invalid(Seq(ValidationError("error.password.minlength")))
    case UserFormData(_, a, b) if a != b =>
      Invalid(Seq(ValidationError("error.password.match")))
    case _ =>
      Valid
  })

  /** Form for managing a Persons details. */
  private[this] val userDataForm = Form(
    mapping(
      FormID.userMail            -> email,
      FormID.userPassword        -> optional(text),
      FormID.userPasswordConfirm -> optional(text),
    )(UserFormData.apply)(UserFormData.unapply).verifying(checkPasswordEquality)
  )

  /** Display the User profile form. */
  def userProfile: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    val query = userTable.filter(_.id === user.userID)
    db.run(query.result).map {
      case Seq(dbUser: User) =>
        val form = userDataForm.bind(Map(
          FormID.userMail -> dbUser.email
        ))
        Ok(user_profile(form))
    }
  }

  /** Check and modify user data. */
  def userProfilePost: EssentialAction = isAuthenticatedAsync { implicit user => implicit request =>
    userDataForm.bindFromRequest.fold(
      formWithErrors => {
        Logger.debug(s"Sending back $formWithErrors")
        Future.successful(BadRequest(user_profile(formWithErrors)))
      },
      modifyPersonData => {
        val filteredTable = userTable.filter(_.id === user.userID)
        val updateQuery = modifyPersonData.userPassword match {
          case Some(newPassword) =>
            filteredTable.map(u => (u.email, u.hash))
              .update((modifyPersonData.userMail, passwordUtil.hash(newPassword)))
          case _ =>
            filteredTable.map(_.email)
              .update(modifyPersonData.userMail)
        }
        db.run(updateQuery).map { _ =>
          Redirect(routes.SettingsController.userProfile()).flashing(FlashKey.UserProfileUpdated -> "")
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
  case class UserFormData(
    userMail: String,
    userPassword: Option[String],
    userPasswordConfirm: Option[String]
  )

  object FormID {
    val userMail = "userMail"
    val userPassword = "userPassword"
    val userPasswordConfirm = "userPasswordConfirm"
  }
}
