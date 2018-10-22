package utils.navigation

import play.api.mvc.Call
import play.api.mvc.RequestHeader

sealed trait NavigationItem

case class NavigationEntry(
  title: String,
  icon: String,
  target: Call,
)(implicit request: RequestHeader) extends NavigationItem {
  def active: Boolean = request.uri == target.url
}

case class NavigationTitle(
  title: String,
  icon: String,
  target: Call,
  subItems: Seq[NavigationEntry] = Seq.empty
)(implicit request: RequestHeader) extends NavigationItem {
  def active: Boolean = request.uri == target.url
}
