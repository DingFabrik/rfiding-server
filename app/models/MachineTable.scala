package models

import slick.jdbc.JdbcProfile
import Index.machineTableIndex

/** Convenience class for a Machine. */
case class Machine(
  id: Option[Int],
  hostname: String,
  macAddress: String,
  name: Option[String],
  isActive: Boolean
)
class MachineTableBuilder(val profile: JdbcProfile) {
  import profile.api._
class MachineTable(tag: Tag) extends Table[Machine](tag, "tb_machine") {

  def id: Rep[Int] = column[Int]("pk_id", O.PrimaryKey, O.AutoInc)
  def hostname: Rep[String] = column[String]("dt_name")
  def macAddress: Rep[String] = column[String]("dt_mac_address")
  def name: Rep[Option[String]] = column[Option[String]]("dt_comment")
  def isActive: Rep[Boolean] = column[Boolean]("dt_active")

  def * = {
    (id.?, hostname, macAddress, name, isActive) <> (Machine.tupled, Machine.unapply)
  }

  def idx = {
    index(machineTableIndex, macAddress, unique = true)
  }
}
}