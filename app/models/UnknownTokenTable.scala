package models

import java.time.LocalDateTime

import slick.jdbc.JdbcProfile
import slick.lifted.ProvenShape
import utils.CustomIsomorphisms.localDateTimeIsomorphism
import utils.CustomIsomorphisms.seqByteIsomorphism

case class UnknownToken(
  serial: Seq[Byte],
  machineId: Int,
  readStamp: LocalDateTime
)

class UnknownTokenTableBuilder(val profile: JdbcProfile) {
  import profile.api._
  val machineBuilder = new MachineTableBuilder(profile)

class UnknownTokenTable(tag: Tag) extends Table[UnknownToken](tag, "tb_unknown_token") {
  val machineTable = TableQuery[machineBuilder.MachineTable]

  def serial: Rep[Seq[Byte]] = column[Seq[Byte]]("dt_serial")
  def machineId: Rep[Int] = column[Int]("fk_machine_id")
  def readStamp: Rep[LocalDateTime] = column[LocalDateTime]("dt_read_stamp")

  def * : ProvenShape[UnknownToken] = {
    (serial, machineId, readStamp) <> ((UnknownToken.apply _).tupled, UnknownToken.unapply)
  }

  def machine = {
    foreignKey("fk_machine", machineId, machineTable)(_.id)
  }
}
}