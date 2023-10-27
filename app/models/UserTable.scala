package models

import slick.jdbc.JdbcProfile

case class User(
  id: Option[Int],
  name: String,
  email: String,
  hash: String
)

/**
 * Table is used to store users that have access to this system.
 */
 class UserTableBuilder(val profile: JdbcProfile) {
  import profile.api._
class UserTable(tag: Tag) extends Table[User](tag, "tb_user") {

  def id: Rep[Int] = column[Int]("pk_id", O.PrimaryKey, O.AutoInc)
  def name: Rep[String] = column[String]("dt_name")
  def email: Rep[String] = column[String]("dt_email", O.Unique)
  def hash: Rep[String] = column[String]("dt_hash")

  def * = {
    (id.?, name, email, hash) <> (User.tupled, User.unapply)
  }
}
 }