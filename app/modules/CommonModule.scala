package modules

import com.google.inject.AbstractModule
import controllers.security.Argon2PasswordUtil
import controllers.security.PasswordUtil
import utils.DefaultSummarizer
import utils.Summarizer
import utils.navigation.DefaultNavigation
import utils.navigation.NavigationComponent

/** Default components to be used by DI. */
class CommonModule extends AbstractModule {
  override def configure(): Unit = {

    bind(classOf[Summarizer])
      .to(classOf[DefaultSummarizer])

    bind(classOf[NavigationComponent])
      .to(classOf[DefaultNavigation])

    bind(classOf[PasswordUtil])
      .to(classOf[Argon2PasswordUtil])

  }
}
