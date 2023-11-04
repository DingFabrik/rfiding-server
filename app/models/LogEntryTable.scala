package models

import java.time.LocalDateTime
import slick.jdbc.JdbcProfile
import Index.machineTableIndex
import slick.model.ForeignKeyAction.Restrict
import utils.CustomIsomorphisms.localDateTimeIsomorphism

case class LogEntry(
  machineId: Int,
  tokenId: Int,
  accessAt: LocalDateTime
)
class LogEntryTableBuilder(val profile: JdbcProfile) {
  import profile.api._
  val machineBuilder = new MachineTableBuilder(profile)

class LogEntryTable(tag: Tag) extends Table[LogEntry](tag, "tb_log_entry") {
    val machineTable = TableQuery[machineBuilder.MachineTable]

    def machineId: Rep[Int] = column[Int]("fk_machine_id")
    def tokenId: Rep[Int] = column[Int]("fk_token_id")
    def accessAt: Rep[LocalDateTime] = column[LocalDateTime]("dt_access_at")

  def * = {
    (machineId, tokenId, accessAt) <> (LogEntry.tupled, LogEntry.unapply)
  }

  def machine = {
    foreignKey("fk_machine", machineId, machineTable)(_.id, onDelete = Restrict)
  }
}
}