package controllers.security

import controllers.security.LoginState.User
import play.api.mvc.AnyContent
import play.api.mvc.BaseController
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesBaseController
import play.api.mvc.MessagesRequest
import play.api.mvc.Request
import play.api.mvc.RequestHeader
import play.api.mvc.Result
import play.api.mvc.Results
import play.api.mvc.Security.Authenticated
import play.api.mvc.Security.WithAuthentication

import scala.concurrent.Future

trait Security {
  controller: BaseController =>

  def userID(request: RequestHeader): Option[Int] = {
    request.session.get(SessionKeys.UserID).map(_.toInt)
  }

  def onUnauthorized(request: RequestHeader) = Results.Redirect(controllers.routes.LoginController.login)


  def isAuthenticated(f: => User => Request[AnyContent] => Result): EssentialAction = {
    Authenticated[Int](userID, onUnauthorized) { userInt: Int =>
      val user = User(userInt)
      controller.Action(request => f(user)(request))
    }
  }

  def isAuthenticatedAsync(f: => User => Request[AnyContent] => Future[Result]): EssentialAction = {
    Authenticated[Int](userID, onUnauthorized) { userInt =>
      val user = User(userInt)
      controller.Action.async(request => f(user)(request))
    }
  }
}

trait MessagesSecurity {
  controller: MessagesBaseController =>

  def userID(request: RequestHeader): Option[Int] = {
    request.session.get(SessionKeys.UserID).map(_.toInt)
  }

  def isAuthenticated(f: => User => MessagesRequest[AnyContent] => Result): EssentialAction = {
    WithAuthentication[Int](userID) { userInt: Int =>
      val user = User(userInt)
      controller.Action(request => f(user)(request))
    }
  }

  def isAuthenticatedAsync(f: => User => MessagesRequest[AnyContent] => Future[Result]): EssentialAction = {
    WithAuthentication[Int](userID) { userInt =>
      val user = User(userInt)
      controller.Action.async(request => f(user)(request))
    }
  }
}
