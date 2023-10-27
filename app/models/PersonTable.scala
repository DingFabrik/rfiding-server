package models

import slick.jdbc.JdbcProfile

/** Convenience class for a Person. */
case class Person(
  id: Option[Int],
  memberId: Option[String],
  name: String,
  email: Option[String],
  isActive: Boolean
)

/**
 * Table is used to store persons that may hold a token.
 */
class PersonTableBuilder(val profile: JdbcProfile) {
  import profile.api._
  class PersonTable(tag: Tag) extends Table[Person](tag, "tb_person") {

  def id: Rep[Int] = column[Int]("pk_id", O.PrimaryKey, O.AutoInc)
  def memberId: Rep[Option[String]] = column[Option[String]]("dt_member_id")
  def name: Rep[String] = column[String]("dt_name")
  def email: Rep[Option[String]] = column[Option[String]]("dt_email")
  //def comment: Rep[Option[String]] = column[Option[String]]("dt_name")
  def isActive: Rep[Boolean] = column[Boolean]("dt_active")

  def * = {
    (id.?, memberId, name, email, isActive) <> (Person.tupled, Person.unapply)
  }
}
}