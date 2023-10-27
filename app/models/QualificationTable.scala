package models

import slick.jdbc.JdbcProfile
import slick.lifted.ProvenShape
import models.Index.qualificationTableIndex
import slick.lifted.ForeignKeyQuery
import slick.lifted.{Index => SlickIndex}
import slick.model.ForeignKeyAction.Restrict

/**
 * Qualification representation.
 *
 * A person must be qualified to use a machine. Otherwise the access is denies.
 *
 * @param machineId The machine ID
 * @param personId  The person ID
 * @param comment   Optional comment about how the qualification was obtained
 */
case class Qualification(
  machineId: Int,
  personId: Int,
  comment: Option[String],
)

class QualificationTableBuilder(val profile: JdbcProfile) {
  import profile.api._
  val machineBuilder = new MachineTableBuilder(profile)
  val personBuilder = new PersonTableBuilder(profile)
class QualificationTable(tag: Tag) extends Table[Qualification](tag, "tb_qualification") {
  val machineTable = TableQuery[machineBuilder.MachineTable]
  val personTable = TableQuery[personBuilder.PersonTable]

  def machineId: Rep[Int] = column[Int]("fk_machine_id")
  def personId: Rep[Int] = column[Int]("fk_person_id")
  def comment: Rep[Option[String]] = column[Option[String]]("dt_comment")

  def * : ProvenShape[Qualification] = {
    (machineId, personId, comment) <> (Qualification.tupled, Qualification.unapply)
  }

  def machine: ForeignKeyQuery[machineBuilder.MachineTable, Machine] = {
    foreignKey("fk_machine", machineId, machineTable)(_.id, onDelete = Restrict)
  }
  def person: ForeignKeyQuery[personBuilder.PersonTable, Person] = {
    foreignKey("fk_person", personId, personTable)(_.id, onDelete = Restrict)
  }

  def idx: SlickIndex = {
    index(qualificationTableIndex, (machineId, personId), unique = true)
  }
}
}