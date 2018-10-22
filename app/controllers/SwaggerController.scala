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
import play.filters.headers.SecurityHeadersFilter.CONTENT_SECURITY_POLICY_HEADER
import slick.jdbc.JdbcProfile
import utils.database.TableProvider
import utils.navigation.NavigationComponent
import views.html.swagger_index

import scala.concurrent.ExecutionContext

@Singleton
/**
 * Swagger UI frontend.
 */
class SwaggerController @Inject()(
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

  private[this] val policy = CONTENT_SECURITY_POLICY_HEADER -> "default-src 'self'; img-src 'self' data:; script-src 'self' http://localhost:9000; style-src 'unsafe-inline' 'self'"

  /** Show Swagger UI index page. */
  def docs = Action {
    Ok(swagger_index()).withHeaders(policy)
  }

  /**
   * Swagger UI javascript.
   *
   * Using a specific route to have dynamic URL resolving.
   */
  def swaggerInlineJs: EssentialAction = Action {
    Ok(views.js.javascript.swagger_inline()).as(JAVASCRIPT)//.withHeaders(policy)
  }

}
