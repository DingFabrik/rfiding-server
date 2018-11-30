package utils.database

import models.MachineConfigTable
import models.MachineTable
import models.MachineTimesTable
import models.PersonTable
import models.PreparedTokenTable
import models.QualificationTable
import models.TokenTable
import models.UnknownTokenTable
import models.UserTable
import slick.lifted.TableQuery

trait TableProvider {
  protected[this] val personTable        = TableQuery[PersonTable]
  protected[this] val tokenTable         = TableQuery[TokenTable]
  protected[this] val unknownTokenTable  = TableQuery[UnknownTokenTable]
  protected[this] val preparedTokenTable = TableQuery[PreparedTokenTable]
  protected[this] val userTable          = TableQuery[UserTable]
  protected[this] val machineTable       = TableQuery[MachineTable]
  protected[this] val machineConfigTable = TableQuery[MachineConfigTable]
  protected[this] val machineTimesTable  = TableQuery[MachineTimesTable]
  protected[this] val qualificationTable = TableQuery[QualificationTable]

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
