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
  runtimer: Option[Long],
  minPower: Option[Long],
  controlParameter: Option[String],
)

class MachineConfigTable(tag: Tag) extends Table[MachineConfig](tag, "tb_machine_config") {
  val machineTable = TableQuery[MachineTable]

  def machineId: Rep[Int] = column[Int]("fk_machine_id")
  def runtimer: Rep[Option[Long]] = column[Option[Long]]("dt_runtimer")
  def minPower: Rep[Option[Long]] = column[Option[Long]]("dt_min_power")
  def controlPararamer: Rep[Option[String]] = column[Option[String]]("dt_ctrl_parameter")

  def * : ProvenShape[MachineConfig] = {
    (machineId, runtimer, minPower, controlPararamer) <> (MachineConfig.tupled, MachineConfig.unapply)
  }

  def machine = {
    foreignKey("fk_machine", machineId, machineTable)(_.id, onDelete = Restrict)
  }

  def idx = {
    index(machineConfigTableIndex, (machineId, runtimer, minPower, controlPararamer), unique = true)
  }
}
