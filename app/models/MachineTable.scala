package models

import slick.jdbc.SQLiteProfile.api._
import Index.machineTableIndex

/** Convenience class for a Machine. */
case class Machine(
  id: Option[Int],
  name: String,
  macAddress: String,
  comment: Option[String],
  isActive: Boolean
)

class MachineTable(tag: Tag) extends Table[Machine](tag, "tb_machine") {

  def id: Rep[Int] = column[Int]("pk_id", O.PrimaryKey, O.AutoInc)
  def name: Rep[String] = column[String]("dt_name")
  def macAddress: Rep[String] = column[String]("dt_mac_address")
  def comment: Rep[Option[String]] = column[Option[String]]("dt_comment")
  def isActive: Rep[Boolean] = column[Boolean]("dt_active")

  def * = {
    (id.?, name, macAddress, comment, isActive) <> (Machine.tupled, Machine.unapply)
  }

  def idx = {
    index(machineTableIndex, macAddress, unique = true)
  }
}
