package controllers

/**
 * Centralizing flashing keys.
 *
 * == CAVEAT ==
 * Keep the keys (and their) values unique
 */
object FlashKey {
  /** When person data was updated. Content: ID of updated person. */
  val PersonUpdated = "personUpdated"
  /** When a person was added to the DB. Content: ID of new person. */
  val PersonAdded = "personAdded"
  /** When a person was deleted. Content: ID of deleted person. */
  val DeletedPerson = "deletedPerson"
  /** When a person was not found in the database. Content: don't care.  */
  val PersonNotFound = "personNotFound"

  /** When a new token was added or copied from the table of prepared tokens. Content: ID of added token. */
  val TokenAdded = "tokenAdded"
  /** When a token was updated. Content: ID of updated token. */
  val UpdatedToken = "updatedToken"
  /** When a token was deleted. Content: ID of deleted token. */
  val DeletedToken = "deletedToken"
  /** When a token couldn't be copied. Content: don't care. */
  val CannotCopyToken = "cannotCopyToken"

  /** When login failed. Content: Reason why login failed. */
  val LoginError = "loginError"
  /** When user logged out. Content: don't care. */
  val LoggedOut = "loggedOut"

  /** When a machine was updated in the DB. Content: ID of updated machine. */
  val MachineTimesUpdated = "machineTimesUpdated"
  val MachineUpdated = "machineUpdated"

  /** When list of unknown tokens was emptied. Content: Nothing. */
  val ListEmptied = "listEmptied"
}
