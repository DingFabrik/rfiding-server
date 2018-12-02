package utils.navigation

import play.api.mvc.RequestHeader

class DefaultNavigation extends NavigationComponent {

  def navigationItems(implicit request: RequestHeader): Seq[NavigationItem] = {
    Seq(
      NavigationEntry(
        title  = s"Tokens",
        icon   = "radio",
        target = controllers.routes.TokenController.listTokens()
      ),
//      NavigationTitle(
//        title  = s"Tokens",
//        icon   = "radio",
//        target = controllers.routes.TokenController.listTokens(),
//        subItems = Seq(
//          NavigationEntry(
//            title  = s"List Tokens",
//            icon   = "radio",
//            target = controllers.routes.TokenController.listTokens()
//          ),
//          NavigationEntry(
//            title  = s"Prepared Tokens",
//            icon   = "radio",
//            target = controllers.routes.TokenController.showPreparedToken()
//          ),
//          NavigationEntry(
//            title  = s"Unknown Tokens",
//            icon   = "radio",
//            target = controllers.routes.TokenController.listUnknownTokens()
//          ),
//        )
//      ),
      NavigationEntry(
        title  = "Persons",
        icon   = "users",
        target = controllers.routes.PersonController.listPersons(),
      ),
//      NavigationTitle(
//        title  = "Persons",
//        icon   = "users",
//        target = controllers.routes.PersonController.listPersons(),
//        subItems = Seq(
//          NavigationEntry(
//            title  = s"List Persons",
//            icon   = "user",
//            target = controllers.routes.PersonController.listPersons()
//          ),
//          NavigationEntry(
//            title  = s"Add Person",
//            icon   = "user-plus",
//            target = controllers.routes.PersonController.addPerson()
//          ),
//        )
//      ),
      NavigationEntry(
        title  = s"Machines",
        icon   = "user",
        target = controllers.routes.MachineController.listMachines()
      ),
//      NavigationTitle(
//        title  = "Machines",
//        icon   = "hard-drive",
//        target = controllers.routes.MachineController.listMachines(),
//        subItems = Seq(
//          NavigationEntry(
//            title  = s"List Machines",
//            icon   = "user",
//            target = controllers.routes.MachineController.listMachines()
//          ),
//          NavigationEntry(
//            title  = s"Add Machine",
//            icon   = "user",
//            target = controllers.routes.MachineController.addMachine()
//          ),
//        )
//      ),
      NavigationTitle(
        title    = "Devel",
        icon     = "settings",
        target   = controllers.routes.Development.apiStuff(),
        subItems = Seq(
          NavigationEntry(
            title   = "Create dummy prepared tokens",
            icon    = "settings",
            target  = controllers.routes.Development.createDummyData()
          ),
          NavigationEntry(
            title  = s"Prepared Tokens",
            icon   = "radio",
            target = controllers.routes.TokenController.showPreparedToken()
          ),
          NavigationEntry(
            title   = "Show API urls",
            icon    = "settings",
            target  = controllers.routes.Development.apiStuff()
          ),
          NavigationEntry(
            title   = "Database schemas",
            icon    = "settings",
            target  = controllers.routes.Development.schemas()
          ),
          NavigationEntry(
            title   = "API Logs",
            icon    = "settings",
            target  = controllers.routes.Development.showLog()
          ),
        )
      ),
      NavigationTitle(
        title    = "API Doc",
        icon     = "settings",
        target   = controllers.routes.SwaggerController.docs(),
        subItems = Seq(
          NavigationEntry(
            title   = "Show Swagger API docs",
            icon    = "settings",
            target  = controllers.routes.SwaggerController.docs()
          ),
        )
      ),

    )
  }
}

object DefaultNavigation {

}
