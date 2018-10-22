package utils.database

import models.MachineConfigTable
import models.PersonTable
import models.PreparedTokenTable
import models.TokenTable
import models.UserTable
import models.MachineTable
import models.MachineTimesTable
import slick.lifted.TableQuery

trait TableProvider {
  protected[this] val personTable        = TableQuery[PersonTable]
  protected[this] val tokenTable         = TableQuery[TokenTable]
  protected[this] val preparedTokenTable = TableQuery[PreparedTokenTable]
  protected[this] val userTable          = TableQuery[UserTable]
  protected[this] val machineTable       = TableQuery[MachineTable]
  protected[this] val machineConfigTable = TableQuery[MachineConfigTable]
  protected[this] val machineTimesTable  = TableQuery[MachineTimesTable]

  protected[this] val allTables = Seq(
    personTable,
    tokenTable,
    preparedTokenTable,
    userTable,
    machineTable,
    machineConfigTable,
    machineTimesTable
  )
}
