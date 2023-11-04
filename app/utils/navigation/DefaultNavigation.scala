package utils.navigation

import play.api.mvc.RequestHeader

class DefaultNavigation extends NavigationComponent {

  def navigationItems(implicit request: RequestHeader): Seq[NavigationItem] = {
    Seq(
      NavigationEntry(
        title  = "Tokens",
        icon   = "radio",
        target = controllers.routes.TokenController.listTokens
      ),
      NavigationEntry(
        title  = "People",
        icon   = "users",
        target = controllers.routes.PersonController.listPersons,
      ),
      NavigationEntry(
        title  = "Machines",
        icon   = "hard-drive",
        target = controllers.routes.MachineController.listMachines
      ),
      NavigationEntry(
        title  = "Access Log",
        icon   = "list",
        target = controllers.routes.LogEntryController.listLogEntries(None, None)
      ),
      NavigationTitle(
        title    = "Devel",
        icon     = "settings",
        target   = controllers.routes.Development.showLog,
        subItems = Seq(
          NavigationEntry(
            title   = "Create dummy prepared tokens",
            icon    = "plus-circle",
            target  = controllers.routes.Development.createDummyData
          ),
          NavigationEntry(
            title  = "Prepared Tokens",
            icon   = "radio",
            target = controllers.routes.TokenController.showPreparedToken
          ),
          NavigationEntry(
            title   = "API Logs",
            icon    = "list",
            target  = controllers.routes.Development.showLog
          ),
        )
      ),
    )
  }
}

object DefaultNavigation {

}
