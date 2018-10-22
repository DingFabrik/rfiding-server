package models

import slick.jdbc.SQLiteProfile.api._

case class User(
  id: Option[Int],
  email: String,
  hash: String
)

/**
 * Table is used to store users that have access to this system.
 */
class UserTable(tag: Tag) extends Table[User](tag, "tb_user") {

  def id: Rep[Int] = column[Int]("pk_id", O.PrimaryKey, O.AutoInc)
  def email: Rep[String] = column[String]("dt_email", O.Unique)
  def hash: Rep[String] = column[String]("dt_hash")

  def * = {
    (id.?, email, hash) <> (User.tupled, User.unapply)
  }
}
