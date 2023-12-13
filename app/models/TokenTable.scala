package models

import models.Index.tokenTableIndex
import slick.jdbc.JdbcProfile
import slick.lifted.ProvenShape
import slick.model.ForeignKeyAction.Restrict
import utils.CustomIsomorphisms.seqByteIsomorphism

/**
  * Convenience class for a Token.
  *
  * @param id        Internal Database ID of this token.
  * @param serial    Serial ID stored on token. Length: 5 Bytes.
  * @param purpose   Purpose of this token.
  * @param isActive  Whether this token is active or not.
  * @param ownerId   FK to the owner of this token.
  */
case class Token(
  id: Option[Int],
  serial: Seq[Byte],
  purpose: Option[String],
  isActive: Boolean,
  ownerId: Int
)

/**
 * Table stores all the available tokens and their owners.
 */
class TokenTableBuilder(val profile: JdbcProfile) {
  import profile.api._
  val personBuilder = new PersonTableBuilder(profile)

  class TokenTable(tag: Tag) extends Table[Token](tag, "tb_token") {
    val personTable = TableQuery[personBuilder.PersonTable]

    def id: Rep[Int] = column[Int]("pk_id", O.PrimaryKey, O.AutoInc)
    def serial: Rep[Seq[Byte]] = column[Seq[Byte]]("dt_serial")
    def purpose: Rep[String] = column[String]("dt_purpose")
    def isActive: Rep[Boolean] = column[Boolean]("dt_active")

    def ownerId: Rep[Int] = column[Int]("fk_owner_id")

    def * : ProvenShape[Token] = {
      (id.?, serial, purpose.?, isActive, ownerId) <> ((Token.apply _).tupled, Token.unapply)
    }

    def owner = {
      foreignKey("fk_owner", ownerId, personTable)(_.id, onDelete = Restrict)
    }

    def idx = {
      index(tokenTableIndex, serial, unique = true)
    }
  }
}