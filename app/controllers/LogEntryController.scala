package controllers

import controllers.PersonController.FormID
import controllers.PersonController.PersonFormData
import controllers.PersonController.PersonQualification
import controllers.PersonController.SimplifiedPerson
import controllers.security.Security
import javax.inject.Inject
import javax.inject.Singleton
import models.Machine
import models.Person
import utils.PaginatedResult
import play.api.Logger
import play.api.data.Form
import play.api.data.Forms.boolean
import play.api.data.Forms.default
import play.api.data.Forms.email
import play.api.data.Forms.mapping
import play.api.data.Forms.number
import play.api.data.Forms.optional
import play.api.data.Forms.text
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.i18n.I18nSupport
import play.api.libs.json.JsSuccess
import play.api.libs.json.Json
import play.api.libs.json.Json.toJson
import play.api.libs.json.Writes
import play.api.mvc.MessagesAbstractController
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesActionBuilder
import play.api.mvc.MessagesControllerComponents
import slick.jdbc.JdbcProfile
import slick.basic.DatabaseConfig
import utils.database.TableProvider
import utils.navigation.NavigationComponent
import views.html.list_log_entries
import play.api.Configuration

import scala.concurrent.ExecutionContext
import scala.concurrent.Future

//noinspection MutatorLikeMethodIsParameterless
@Singleton
class LogEntryController @Inject()(
  protected val dbConfigProvider: DatabaseConfigProvider,
  messagesAction: MessagesActionBuilder,
  mc: MessagesControllerComponents,
  config: Configuration
)(
  implicit ec: ExecutionContext,
  navigation: NavigationComponent,
) extends MessagesAbstractController(mc)
  with I18nSupport
  with TableProvider
  with Security {
  controller =>
  import profile.api._

  private[this] val logger: Logger = Logger("api")

  def findAll(limit: Int, offset: Int, machineId: Option[Int] = None) = db.run {
    var query = logEntryTable.filter( m => machineId.fold(true.bind)(m.machineId === _))
    for {
        entries <- query
            .sortBy(_.accessAt.desc)
            .joinLeft(machineTable).on {
                case (entry, machine) => entry.machineId === machine.id
            }
            .drop(offset)
            .take(limit)
            .result
        numberOfEntries <- query.length.result
    } yield PaginatedResult(
        totalCount = numberOfEntries,
        currentOffset = offset,
        entities = entries.toList,
        hasNextPage = numberOfEntries - (offset + limit) > 0,
        pageSize = limit
    )
  }

  /** Returns all persons in the database. */
  def listLogEntries(offset: Option[Int], machineId: Option[Int] = None): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val future = for {
        entries <- findAll(config.get[Int]("app.pageSize"), offset.getOrElse(0), machineId)
        machines <- db.run(machineTable.sortBy(_.name).result)
    } yield Tuple2(entries, machines)
    
    future.map { case (entries, machines) =>
      Ok(list_log_entries(entries, machines, machineId))
    }
  }
}
