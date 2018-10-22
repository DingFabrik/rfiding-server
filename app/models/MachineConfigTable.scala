package models

import slick.jdbc.SQLiteProfile.api._
import slick.lifted.ProvenShape
import slick.model.ForeignKeyAction.Restrict
import models.Index.machineConfigTableIndex

/**
 * Storage for a machine configuration
 *
 * @param machineId  The machines ID
 * @param runtimer   Time a machine may be idle before turning off.
 */
case class MachineConfig(
  machineId: Int,
  runtimer: Long
)

class MachineConfigTable(tag: Tag) extends Table[MachineConfig](tag, "tb_machine_config") {
  val machineTable = TableQuery[MachineTable]

  def machineId: Rep[Int] = column[Int]("fk_machine_id")
  def runtimer: Rep[Long] = column[Long]("dt_runtimer")

  def * : ProvenShape[MachineConfig] = {
    (machineId, runtimer) <> (MachineConfig.tupled, MachineConfig.unapply)
  }

  def machine = {
    foreignKey("fk_machine", machineId, machineTable)(_.id, onDelete = Restrict)
  }

  def idx = {
    index(machineConfigTableIndex, (machineId, runtimer), unique = true)
  }
}
