package utils.database

import play.api.db.slick.HasDatabaseConfigProvider
import slick.basic.DatabaseConfig
import slick.jdbc.JdbcProfile
import models.LogEntryTableBuilder
import models.MachineConfigTableBuilder
import models.MachineTableBuilder
import models.MachineTimesTableBuilder
import models.PersonTableBuilder
import models.PreparedTokenTableBuilder
import models.QualificationTableBuilder
import models.TokenTableBuilder
import models.UnknownTokenTableBuilder
import models.UserTableBuilder
import slick.lifted.TableQuery

trait TableProvider extends HasDatabaseConfigProvider[JdbcProfile] {

  val logEntryBuilder = new LogEntryTableBuilder(profile)
  protected[this] val logEntryTable      = TableQuery[logEntryBuilder.LogEntryTable]
  val personBuilder = new PersonTableBuilder(profile)
  protected[this] val personTable        = TableQuery[personBuilder.PersonTable]
  val tokenBuilder = new TokenTableBuilder(profile)
  protected[this] val tokenTable         = TableQuery[tokenBuilder.TokenTable]
  val unknownTokenBuilder = new UnknownTokenTableBuilder(profile)
  protected[this] val unknownTokenTable  = TableQuery[unknownTokenBuilder.UnknownTokenTable]
  val preparedTokenBuilder = new PreparedTokenTableBuilder(profile)
  protected[this] val preparedTokenTable = TableQuery[preparedTokenBuilder.PreparedTokenTable]
  val userBuilder = new UserTableBuilder(profile)
  protected[this] val userTable          = TableQuery[userBuilder.UserTable]
  val machineBuilder = new MachineTableBuilder(profile)
  protected[this] val machineTable       = TableQuery[machineBuilder.MachineTable]
  val machineConfigBuilder = new MachineConfigTableBuilder(profile)
  protected[this] val machineConfigTable = TableQuery[machineConfigBuilder.MachineConfigTable]
  val machineTimesBuilder = new MachineTimesTableBuilder(profile)
  protected[this] val machineTimesTable  = TableQuery[machineTimesBuilder.MachineTimesTable]
  val qualificationBuilder = new QualificationTableBuilder(profile)
  protected[this] val qualificationTable = TableQuery[qualificationBuilder.QualificationTable]

  protected[this] val allTables = Seq(
    personTable,
    tokenTable,
    unknownTokenTable,
    preparedTokenTable,
    userTable,
    machineTable,
    machineConfigTable,
    machineTimesTable,
    qualificationTable
  )
}
