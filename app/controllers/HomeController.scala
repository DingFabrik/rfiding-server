package controllers

import controllers.security.LoginState.User
import controllers.security.Security
import controllers.security.SessionKeys
import javax.inject.Inject
import javax.inject.Singleton
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.mvc.AbstractController
import play.api.mvc.AnyContent
import play.api.mvc.ControllerComponents
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesActionBuilder
import play.api.mvc.Request
import slick.jdbc.JdbcProfile
import slick.basic.DatabaseConfig
import utils.database.TableProvider
import utils.navigation.NavigationComponent
import views.html.index_logged_in
import views.html.index_logged_out

import scala.concurrent.ExecutionContext
import scala.concurrent.Future


/**
 * This controller creates an `Action` to handle HTTP requests to the
 * application's home page.
 */
@Singleton
class HomeController @Inject()(
  protected val dbConfigProvider: DatabaseConfigProvider,
  messagesAction: MessagesActionBuilder,
  cc: ControllerComponents
)(
  implicit ec: ExecutionContext,
  navigation: NavigationComponent,
) extends AbstractController(cc)
    with HasDatabaseConfigProvider[JdbcProfile]
    with TableProvider
    with Security {

  import profile.api._

  def index: EssentialAction = Action.async { implicit request =>
    userID(request).fold(Future.successful(Ok(index_logged_out()))) { userId =>
      val query = (personTable.length zip personTable.filter(_.isActive === true).length) zip (tokenTable.length zip tokenTable.filter(_.isActive === true).length) zip (machineTable.length zip machineTable.filter(_.isActive === true).length)
      db.run(query.result).map { case (((personLength, activePerson), (tokenLength, activeToken)), (machineLength, activeMachine)) =>
        Ok(index_logged_in(User(userId), personLength, activePerson, tokenLength, activeToken, machineLength, activeMachine))
      }
    }
  }

  /** Displays autocomplete javascript for persons. */
  def autocompletePersonJs: EssentialAction = Action {
    Ok(views.js.javascript.autocomplete_person()).as(JAVASCRIPT)
  }

  /** Displays autocomplete javascript for machines. */
  def autocompleteMachineJs(userId: Int): EssentialAction = Action {
    Ok(views.js.javascript.autocomplete_machine(userId)).as(JAVASCRIPT)
  }

  /** Loads javascript to toggle active state for tokens. */
  def toggleTokenActive(): EssentialAction = Action {
    Ok(views.js.javascript.toggle_checkbox(routes.TokenController.toggleTokenActivePost)).as(JAVASCRIPT)
  }

  /** Loads javascript to toggle active state for persons. */
  def togglePersonActive(): EssentialAction = Action {
    Ok(views.js.javascript.toggle_checkbox(routes.PersonController.togglePersonActivePost)).as(JAVASCRIPT)
  }

  /** Loads javascript to toggle active state for machines. */
  def toggleMachineActive(): EssentialAction = Action {
    Ok(views.js.javascript.toggle_checkbox(routes.MachineController.toggleMachineActivePost)).as(JAVASCRIPT)
  }

  def filterLogEntry(): EssentialAction = Action {
    Ok(views.js.javascript.filter_log_entry()).as(JAVASCRIPT)
  }
}
