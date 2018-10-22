package controllers.security

sealed trait LoginState

object LoginState {
  case object LoggedOut extends LoginState
  case class User(userID: Int) extends LoginState
}
