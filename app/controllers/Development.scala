package controllers

import de.mkammerer.argon2.Argon2Factory
import de.mkammerer.argon2.Argon2Helper
import javax.inject.Inject
import javax.inject.Singleton
import models.Machine
import models.MachineConfig
import models.MachineTime
import models.Person
import models.PreparedToken
import models.Token
import models.User
import play.api.Configuration
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.mvc.MessagesAbstractController
import play.api.mvc.MessagesControllerComponents
import play.api.mvc.EssentialAction
import slick.jdbc.JdbcProfile
import slick.basic.DatabaseConfig
import utils.database.TableProvider
import utils.navigation.NavigationComponent
import utils.reader.ReaderUtils

import scala.Iterator.continually
import scala.concurrent.ExecutionContext
import scala.io.Source

@Singleton
class Development @Inject()(
  protected val dbConfigProvider: DatabaseConfigProvider,
  cc: MessagesControllerComponents,
  config: Configuration
)(implicit ec: ExecutionContext, navigation: NavigationComponent)
  extends MessagesAbstractController(cc)
    with TableProvider {
  import profile.api._

  /** Helper to create some tables in the db. */
  def setup: EssentialAction = Action.async { implicit request =>
    val setupQuery = DBIO.seq(
      // Commented out to not accidentally create some schemas
      //machineTable.schema.create
    )
    val creationResult = db.run(setupQuery)
    creationResult.map(result => Ok(s"Result of database action: $result"))
  }

  /** Pad a string to 72 chars and fill with asterisks. */
  private[this] def padTable(content: String): String = {
    content + " " + "-" * (72 - content.length)
  }

  /** Fill the prepared token table with dummy data. */
  def createDummyData: EssentialAction = Action.async { implicit request =>
    val dummyData = continually(ReaderUtils.createDummyData(4)).zipWithIndex.take(10).toSeq
    val query = DBIO.sequence(dummyData.map { case (serialSeq, index) =>
      preparedTokenTable += PreparedToken(None, serialSeq, s"Randomly generated serial with index $index")
    })

    db.run(query).map { _ =>
      Ok(views.html.devel.dummy_data(dummyData))
    }
  }


  def showLog: EssentialAction = Action { implicit request =>
    val lines: String = Source.fromFile("logs/application.log")
      .getLines()
      .filter(_.contains("from api "))
      .mkString("\n")
    Ok(views.html.devel.show_log(lines))
  }

}
