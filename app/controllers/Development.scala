package controllers

import de.mkammerer.argon2.Argon2Factory
import de.mkammerer.argon2.Argon2Helper
import javax.inject.Inject
import javax.inject.Singleton
import models.Machine
import models.MachineConfig
import models.MachineConfigTable
import models.MachineTable
import models.MachineTime
import models.MachineTimesTable
import models.Person
import models.PersonTable
import models.PreparedToken
import models.PreparedTokenTable
import models.Token
import models.TokenTable
import models.User
import models.UserTable
import play.api.Configuration
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.mvc.AbstractController
import play.api.mvc.ControllerComponents
import play.api.mvc.EssentialAction
import slick.dbio.DBIO
import slick.jdbc.JdbcProfile
import slick.jdbc.SQLiteProfile
import slick.jdbc.SQLiteProfile.api._
import utils.database.TableProvider
import utils.navigation.NavigationComponent
import utils.reader.ReaderUtils

import scala.Iterator.continually
import scala.concurrent.ExecutionContext
import scala.io.Source

@Singleton
class Development @Inject()(
  protected val dbConfigProvider: DatabaseConfigProvider,
  cc: ControllerComponents,
  config: Configuration
)(implicit ec: ExecutionContext, navigation: NavigationComponent)
  extends AbstractController(cc)
    with HasDatabaseConfigProvider[JdbcProfile]
    with TableProvider {

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

  /** Display table schemas. Uses highlight.js to highlight sql syntax. */
  def schemas: EssentialAction =  Action { implicit request =>
    val creation = allTables.map { table => (table.baseTableRow.tableName, table.schema.createStatements) }
    val destruction = allTables.reverse.map { table => (table.baseTableRow.tableName, table.schema.dropStatements) }

    val builder = new StringBuilder()
    builder.append("# --- !Ups\n")
    creation.foreach { case (name, statements) =>
      builder.append(s"-- TABLE ${padTable(name)}\n")
      statements.foreach(s => builder.append(s + ";\n"))
    }
    builder.append("\n")
    builder.append("# --- !Downs\n")
    destruction.foreach { case (name, statements) =>
      builder.append(s"-- TABLE ${padTable(name)}\n")
      statements.foreach(s => builder.append(s + ";\n"))
    }

    Ok(views.html.devel.show(builder.toString))
  }

  /** Keeping this for future reference. */
  def createSourceCode: EssentialAction = Action { implicit request =>
    val slickDriver = "slick.jdbc.SQLiteProfile"
    val jdbcDriver = "org.sqlite.JDBC"
    val url = "jdbc:sqlite:db.sqlite"
    val outputFolder = "conf/evolutions/default"
    val pkg = "de.dingfabrik.example"

    // Slick source code generator
//    SourceCodeGenerator.main(
//      Array(slickDriver, jdbcDriver, url, outputFolder, pkg)
//    )

    Ok("Done.")
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

  /** Calculate the optimal number of iterations for the Argon2 algorithm. */
  // TODO: Make this method a little more restricted.
  def calculateIteration(memory: Int, parallelism: Int): EssentialAction = Action { implicit request =>
    // Create instance
    val argon2 = Argon2Factory.create()
    val iterations = Argon2Helper.findIterations(argon2, 1000, memory, parallelism)

    Ok(s"Recommended no. of iterations: $iterations")
  }

  def apiStuff: EssentialAction = Action { implicit request =>
    Ok(views.html.show_api_stuff())
  }

  def showLog: EssentialAction = Action { implicit request =>
    val lines: String = Source.fromFile("logs/application.log")
      .getLines()
      .filter(_.contains("from api "))
      .mkString("\n")
    Ok(views.html.devel.show_log(lines))
  }

}
