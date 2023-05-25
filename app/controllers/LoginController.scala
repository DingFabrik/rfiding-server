package controllers

import controllers.LoginController.UserLoginData
import controllers.security.PasswordUtil
import controllers.security.SessionKeys
import javax.inject.Inject
import javax.inject.Singleton
import models.User
import play.api.Logger
import play.api.data.Form
import play.api.data.Forms.email
import play.api.data.Forms.mapping
import play.api.data.Forms.nonEmptyText
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.mvc.AbstractController
import play.api.mvc.AnyContent
import play.api.mvc.ControllerComponents
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesActionBuilder
import play.api.mvc.MessagesRequest
import slick.jdbc.JdbcProfile
import slick.jdbc.SQLiteProfile.api._
import utils.database.TableProvider
import utils.navigation.NavigationComponent

import scala.concurrent.ExecutionContext
import scala.concurrent.Future

@Singleton
class LoginController @Inject()(
  protected val dbConfigProvider: DatabaseConfigProvider,
  messagesAction: MessagesActionBuilder,
  components: ControllerComponents,
  passwordUtil: PasswordUtil
)(implicit ec: ExecutionContext, navigation: NavigationComponent)
  extends AbstractController(components)
    with HasDatabaseConfigProvider[JdbcProfile]
    with TableProvider {

  private[this] val userLoginForm = Form(
    mapping(
      SessionKeys.Email    -> email,
      SessionKeys.Password -> nonEmptyText
    )(UserLoginData.apply)(UserLoginData.unapply)
  )

  /** Present the user login form. */
  def login: EssentialAction = messagesAction { implicit request: MessagesRequest[AnyContent] =>
    Ok(views.html.login(userLoginForm)).withNewSession
  }

  /**
   * Receive input from login mask and evaluate it.
   *
   * The password is hashed with the Argon2 algorithm.
   */
  def loginPost: EssentialAction = messagesAction.async { implicit request: MessagesRequest[AnyContent] =>
    userLoginForm.bindFromRequest.fold(
      formWithErrors => {
        Future.successful(BadRequest(views.html.login(formWithErrors)))
      },
      userLoginData => {
        val userQuery = userTable.filter(_.email === userLoginData.email)
        db.run(userQuery.result).map { user: Seq[User] =>
          if (user.nonEmpty && passwordUtil.verify(user.head.hash, userLoginData.password)) {
            val userID = user.head.id.get.toString
            Redirect(routes.HomeController.index).withSession(SessionKeys.UserID -> userID)
          } else {
            Redirect(routes.LoginController.login).withNewSession.flashing(FlashKey.LoginError -> "Username/Password incorrect.")
          }
        }

      }
    )
  }

  /** Log out user and kill session data. */
  def logout: EssentialAction = Action { implicit request =>
    Redirect(routes.LoginController.login).withNewSession.flashing(FlashKey.LoggedOut -> "loggedOut")
  }
}

object LoginController {
  /** Helper class to handle login form data. */
  case class UserLoginData(email: String, password: String)
}

