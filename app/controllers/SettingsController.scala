package controllers

import controllers.security.Security
import javax.inject.Inject
import javax.inject.Singleton
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.i18n.I18nSupport
import play.api.mvc.AbstractController
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesActionBuilder
import play.api.mvc.MessagesControllerComponents
import slick.jdbc.JdbcProfile
import utils.BuildInfo
import utils.database.TableProvider
import utils.navigation.NavigationComponent

import scala.concurrent.ExecutionContext


@Singleton
class SettingsController @Inject()(
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

  def settings: EssentialAction = Action {
    Ok("settings")
  }

  def about: EssentialAction = isAuthenticated { implicit user => implicit request =>

    Ok(views.html.about())
  }
}
