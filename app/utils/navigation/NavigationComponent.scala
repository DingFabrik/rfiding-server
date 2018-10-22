package utils.navigation

import play.api.mvc.RequestHeader

trait NavigationComponent {
  def navigationItems(implicit request: RequestHeader): Seq[NavigationItem]
}
