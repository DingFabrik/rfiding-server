package controllers.security

import controllers.security.LoginState.User
import play.api.mvc.AnyContent
import play.api.mvc.BaseController
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesBaseController
import play.api.mvc.MessagesRequest
import play.api.mvc.Request
import play.api.mvc.WrappedRequest
import play.api.mvc.RequestHeader
import play.api.mvc.Result
import play.api.mvc.ActionBuilder
import play.api.mvc.Results
import play.api.mvc.Security.Authenticated
import play.api.mvc.Security.WithAuthentication
import play.api.i18n.Lang
import play.api.i18n.LangImplicits

import scala.concurrent.Future

object LanguageAction extends ActionBuilder[MessagesRequest, AnyContent] {
  def invokeBlock[A](request: MessagesRequest[A], block: (MessagesRequest[A]) => Future[Result]) = {

  val newRequest = new WrappedRequest[A](request) {
      //calculate from request url
      val lang = Lang("de")

      override lazy val acceptLanguages = Seq(lang)
    }

    block(newRequest)
  }
}

trait Security extends LangImplicits {
  controller: MessagesBaseController =>

  def userID(request: RequestHeader): Option[Int] = {
    request.session.get(SessionKeys.UserID).map(_.toInt)
  }

  def onUnauthorized(request: RequestHeader) = Results.Redirect(controllers.routes.LoginController.login)


  def isAuthenticated(f: => User => MessagesRequest[AnyContent] => Result): EssentialAction = {
    WithAuthentication[Int](userID) { userInt: Int =>
      val user = User(userInt)
      LanguageAction({request =>
        implicit val lang: Lang = Lang("de")
        f(user)(request)
      })
    }
  }

  def isAuthenticatedAsync(f: => User => MessagesRequest[AnyContent] => Future[Result]): EssentialAction = {
    WithAuthentication[Int](userID) { userInt =>
      val user = User(userInt)
      LanguageAction.async({request =>
        implicit val lang: Lang = Lang("de")
        implicit val messages = lang2Messages
        f(user)(request)
      })
    }
  }
}
