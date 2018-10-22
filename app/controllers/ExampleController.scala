package controllers

import java.time.LocalTime

import controllers.ExampleController.FormData
import javax.inject.Inject
import javax.inject.Singleton
import play.api.Logger
import play.api.data.Form
import play.api.data.Forms.mapping
import play.api.data.Forms.localTime
import play.api.data.Forms.text
import play.api.mvc.AbstractController
import play.api.mvc.ControllerComponents
import play.api.mvc.EssentialAction

@Singleton
class ExampleController @Inject()(
  cc: ControllerComponents
) extends AbstractController(cc) {

  private[this] val simpleForm = {
    Form(
      mapping = mapping(
        "timespan" -> localTime("HH:mm"),
      )(FormData.apply)(FormData.unapply)
    )
  }


  def index: EssentialAction = Action { implicit request =>
    Ok(views.html.example.index(simpleForm))
  }

  def indexPost: EssentialAction = Action { implicit request =>
    simpleForm.bindFromRequest.fold(
      formWithErrors => {
        Ok(s"formWithErrors = $formWithErrors")
      },
      formData => {
        Logger.debug(s"request  = $request")
        Logger.debug(s"body     = ${request.body}")
        Logger.debug(s"formData = ${formData}")
        val t = formData.timespan.toSecondOfDay
        Logger.debug(s"t       = ${t}")
        Ok(views.html.example.result(formData))
      }
    )
  }


}

object ExampleController {
  case class FormData(
    timespan: LocalTime,
    //timespan: String,
  )
}

