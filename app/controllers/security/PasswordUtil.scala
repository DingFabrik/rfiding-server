package controllers.security

import de.mkammerer.argon2.Argon2
import de.mkammerer.argon2.Argon2Factory
import javax.inject.Inject
import play.api.Configuration

import scala.util.Try

/** Base trait for a password util class. */
trait PasswordUtil {

  /**
   * Create hash for the given password using a one-way function.
   *
   * @param password the password to create the hash for
   * @return a hashed password.
   */
  def hash(password: String): String

  /**
   * Check whether a given hash matches to a given password.
   *
   * @param hash The hash to check
   * @param password The password which should be checked against the hash.
   *
   * @return True if the hash matches the password.
   */
  def verify(hash: String, password: String): Boolean
}

/**
 * Reference implementation for the Argon2 algorithm.
 *
 * See https://www.owasp.org/index.php/Password_Storage_Cheat_Sheet for
 * more information about this implementation.
 *
 * Configure the algorithm via application.conf parameters.
 */
class Argon2PasswordUtil @Inject()(config: Configuration) extends PasswordUtil {

  private[this] lazy val parallelism: Int = config.get[Int]("security.argon2.parallelism")
  private[this] lazy val memory: Int = config.get[Int]("security.argon2.memory")
  private[this] lazy val iterations: Int = config.get[Int]("security.argon2.iterations")

  private[this] def createInstance(): Argon2 = {
    Argon2Factory.create()
  }

  /** Create a argon2 hash for the given password. */
  def hash(password: String): String = {
    val argon2 = createInstance()
    val hashTry = Try(argon2.hash(iterations, memory, parallelism, password))
    argon2.wipeArray(password.toCharArray)
    hashTry.getOrElse("")
  }

  /** Verify an argon2 hash against a password. Return true on match. */
  def verify(hash: String, password: String): Boolean = {
    val argon2 = createInstance()
    val verifyTry = Try(argon2.verify(hash, password))
    argon2.wipeArray(password.toCharArray)
    verifyTry.get
  }

}
