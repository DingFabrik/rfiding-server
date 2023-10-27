package models

import models.Index.preparedTokenTableIndex
import slick.jdbc.JdbcProfile
import utils.CustomIsomorphisms.seqByteIsomorphism

/**
  * Convenience class for a prepared Token.
  *
  * @param id        Internal Database ID of this token.
  * @param serial    Serial ID stored on token. Length: 5 Bytes.
  * @param purpose   Purpose of this token.
  */
case class PreparedToken(
  id: Option[Int],
  serial: Seq[Byte],
  purpose: String
)

/**
 * Table stores all the available tokens.
 */
class PreparedTokenTableBuilder(val profile: JdbcProfile) {
  import profile.api._
  class PreparedTokenTable(tag: Tag) extends Table[PreparedToken](tag, "tb_prepared_token") {

  def id: Rep[Int] = column[Int]("pk_id", O.PrimaryKey, O.AutoInc)
  def serial: Rep[Seq[Byte]] = column[Seq[Byte]]("dt_serial")
  def purpose: Rep[String] = column[String]("dt_purpose")


  def * = {
    (id.?, serial, purpose) <> (PreparedToken.tupled, PreparedToken.unapply)
  }

  def idx = {
    index(preparedTokenTableIndex, serial, unique = true)
  }
}
}