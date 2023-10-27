package models

import java.time.LocalTime

import slick.jdbc.JdbcProfile
import utils.CustomIsomorphisms.seqWeekdayIsomorphism
import utils.CustomIsomorphisms.localTimeIsomorphism
import utils.time.Weekday
import Index.machineTimesTableIndex

case class MachineTime(
  id: Option[Int],
  machineId: Int,
  weekdays: Seq[Weekday],
  startTime: LocalTime,
  endTime: LocalTime
)

/**
 * Representation of possible times when a device may or may not be usable
 */
class MachineTimesTableBuilder(val profile: JdbcProfile) {
  import profile.api._
  val machineBuilder = new MachineTableBuilder(profile)

  class MachineTimesTable(tag: Tag) extends Table[MachineTime](tag, "tb_machine_times") {

  // For convenience we add an ID column to properly identify allowed times.
  def id: Rep[Int] = column[Int]("pk_id", O.PrimaryKey, O.AutoInc)

  def machineId: Rep[Int] = column[Int]("fk_machine_id")
  def weekdays: Rep[Seq[Weekday]] = column[Seq[Weekday]]("dt_weekdays")
  def startTime: Rep[LocalTime] = column[LocalTime]("dt_starttime")
  def endTime: Rep[LocalTime] = column[LocalTime]("dt_endtime")

  def * = {
    (id.?, machineId, weekdays, startTime, endTime) <> (MachineTime.tupled, MachineTime.unapply)
  }

  def idx = {
    index(machineTimesTableIndex, id, unique = true)
  }
}
}

