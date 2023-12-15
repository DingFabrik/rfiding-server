package controllers

import controllers.ApiController.formatTokenSeq
import controllers.TokenController.AddTokenData
import controllers.TokenController.FindPersonData
import controllers.TokenController.FormKey
import controllers.TokenController.TokenData
import controllers.security.Security
import javax.inject.Inject
import javax.inject.Singleton
import models.Machine
import models.Person
import models.PreparedToken
import models.Token
import models.UnknownToken
import play.api.Logger
import play.api.data.Form
import play.api.data.Forms.boolean
import play.api.data.Forms.ignored
import play.api.data.Forms.mapping
import play.api.data.Forms.number
import play.api.data.Forms.of
import play.api.data.Forms.optional
import play.api.data.Forms.text
import play.api.db.slick.DatabaseConfigProvider
import play.api.db.slick.HasDatabaseConfigProvider
import play.api.i18n.I18nSupport
import play.api.libs.json.JsSuccess
import play.api.libs.json.Json.toJson
import play.api.mvc.MessagesAbstractController
import play.api.mvc.EssentialAction
import play.api.mvc.MessagesActionBuilder
import play.api.mvc.MessagesControllerComponents
import slick.jdbc.JdbcProfile
import slick.basic.DatabaseConfig
import utils.database.TableProvider
import utils.forms.seqByteFormatter
import utils.navigation.NavigationComponent
import views.html.add_token
import views.html.copy_prepared_token
import views.html.list_assignments
import views.html.list_tokens
import views.html.list_unknown_tokens
import views.html.modify_token
import views.html.show_prepared_token

import scala.concurrent.ExecutionContext
import scala.concurrent.Future

/**
 * Token controller. Handles all actions associated with token handling.
 *
 * @note The term "assign a token" essentially means copy the data from the prepared token table to the token table.
 */
//noinspection MutatorLikeMethodIsParameterless
@Singleton
class TokenController @Inject()(
  protected val dbConfigProvider: DatabaseConfigProvider,
  messagesAction: MessagesActionBuilder,
  mc: MessagesControllerComponents
)(
  implicit ec: ExecutionContext,
  navigation: NavigationComponent,
) extends MessagesAbstractController(mc)
  with TableProvider
  with Security { controller =>
  import profile.api._

  private[this] val logger: Logger = Logger("api")

  import utils.CustomIsomorphisms.seqByteIsomorphism

  /** Form to assign a token to a person. */
  private[this] val findPersonForm = Form(
    mapping(
      FormKey.findPersonId -> number
    )(FindPersonData.apply)(FindPersonData.unapply)
  )

  /** Form to assign a token to a person. */
  private[this] val addTokenForm = Form(
    mapping(
      FormKey.tokenSerial    -> of[Seq[Byte]].verifying("Invalid token length. (4 Bytes)", _.length == 4),
      FormKey.tokenPurpose   -> optional(text),
      FormKey.findPersonId   -> number,
      FormKey.findPersonName -> ignored(""),
    )(AddTokenData.apply)(AddTokenData.unapply)
  )

  def addToken(token: String): EssentialAction = isAuthenticated { implicit userId => implicit request =>
    val tokenSerial: Seq[Byte] = formatTokenSeq(token)
    Ok(add_token(tokenSerial, addTokenForm))
  }

  def addTokenPost: EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
  addTokenForm.bindFromRequest.fold(
    formWithErrors => {
      val tokenAsString = formWithErrors.apply(FormKey.tokenSerial).value.get
      val tokenSerial = formatTokenSeq(tokenAsString)
      Future.successful(BadRequest(add_token(tokenSerial, formWithErrors)))
    },
    addTokenData => {
      val insertQuery = (tokenTable returning tokenTable.map(_.id)) += Token(
          id       = None,
          serial   = addTokenData.serial,
          purpose  = addTokenData.purpose,
          isActive = true,
          ownerId  = addTokenData.personId
        )
        db.run(insertQuery).map { result: Int =>
          Redirect(routes.TokenController.listTokens)
            .flashing(FlashKey.TokenAdded -> result.toString)
        }
      }
    )
  }

  def clearUnknownTokenList: EssentialAction =  isAuthenticatedAsync { implicit userId => implicit request =>
    db.run(unknownTokenTable.delete).map { _ =>
      Redirect(routes.TokenController.listUnknownTokens)
        .flashing(FlashKey.ListEmptied -> "")
    }
  }

  def listTokens: EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val query = tokenTable join personTable on (_.ownerId === _.id)
    db.run(query.result).map { result: Seq[(Token, Person)] =>
      Ok(list_tokens(result))
    }
  }

  def listUnknownTokens: EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val query = unknownTokenTable join machineTable on (_.machineId === _.id)
    db.run(query.result).map { result: Seq[(UnknownToken, Machine)] =>
      Ok(list_unknown_tokens(result))
    }
  }

  /**
   * List of Persons and their assigned tokens.
   *
   * I don't know how to properly render such a list. But as the query is quite complex I leave the code in here.
   */
  def listAssignments: EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    // Query for all persons and an optional token
    val query = for {
      tokens <- tokenTable
      persons <- personTable.sortBy(_.name) if tokens.ownerId === persons.id
    } yield (persons, tokens)
    db.run(query.result).map { result =>
      val groupedResult = result.groupBy { case (personResult, _) => personResult }
      val resultMap = groupedResult.map { case (person, seq: Seq[(Person, Token)]) =>
        val tokens: Seq[Token] = seq.map { case (_, t) => t }
        person -> tokens
      }
      Ok(list_assignments(resultMap))
    }
  }


  /**
   * Shows a list of prepared token.
   *
   * All tokens are displayed. If a token is already assigned to a person, the name of the person is displayed.
   * Otherwise a link to the assignment form.
   */
  def showPreparedToken: EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val tokenQuery = preparedTokenTable.sortBy(_.purpose).joinLeft(tokenTable).on(_.serial === _.serial)
    val withPersonQuery = tokenQuery.joinLeft(personTable).on(_._2.map(_.ownerId) === _.id)
    db.run(withPersonQuery.result).map { tokens: Seq[((PreparedToken, Option[Token]), Option[Person])] =>
      Ok(show_prepared_token(tokens))
    }
  }

  /**
   * Displays the form to assign a token to a person.
   *
   * The person must already exist. An autocomplete mechanism is used to select a person.
   */
  def copyPreparedToken(id: Int): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val preparedToken = preparedTokenTable.filter(_.id === id)
    db.run(preparedToken.result).map {
      case Seq(token) =>
        Ok(copy_prepared_token(token, findPersonForm))
      case _ =>
        BadRequest("Oops. You tried to access a non-existing token...")
    }
  }

  /** Evaluates the form and assignes a token to a person. */
  def copyPreparedTokenPost(id: Int): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    findPersonForm.bindFromRequest.fold(
      formWithErrors => {
        logger.debug(s"formWithErrors: $formWithErrors")

        Future.successful(
          Redirect(routes.TokenController.copyPreparedToken(id)).flashing(FlashKey.CannotCopyToken -> "error")
        )
      },
      // Insert new token by copying data of prepared token.
      copyTokenData => {
        // Lookup prepared token
        val preparedTokenQuery = preparedTokenTable.filter(_.id === id)

        val query = preparedTokenQuery.result.flatMap {
          case Seq(preparedToken: PreparedToken) =>
            (tokenTable returning tokenTable.map(_.id)) += Token(
              id       = None,
              serial   = preparedToken.serial,
              purpose  = Some(preparedToken.purpose),
              isActive = true,
              ownerId  = copyTokenData.id
            )
        }
        db.run(query).map { insertedTokenId: Int =>
          Redirect(routes.PersonController.modifyPerson(copyTokenData.id))
            .flashing(FlashKey.TokenAdded -> insertedTokenId.toString)
        }
      }
    )
  }

  /** Method is called via javascript and toggles activation state of a token. */
  def toggleTokenActivePost(): EssentialAction =  isAuthenticatedAsync { implicit userId => implicit request =>
    request.body.asJson.map { jsValue =>
      ((jsValue \ "id").validate[Int], (jsValue \ "checked").validate[Boolean])
    } match {
      case Some((tokenValue: JsSuccess[Int], checkedValue: JsSuccess[Boolean])) =>
        val query = tokenTable.filter(_.id === tokenValue.get).map(_.isActive).update(checkedValue.get)
        db.run(query).map { _ => Ok(toJson("")) }
      case _ =>
        Future.successful(BadRequest(toJson("")))
    }
  }

  /** Form to assign a token to a person. */
  private[this] val modifyTokenForm: Form[TokenData] = Form(
    mapping(
      FormKey.tokenId       -> number,
      FormKey.tokenPurpose  -> optional(text),
      FormKey.tokenIsActive -> boolean
    )(TokenData.apply)(TokenData.unapply)
  )

  def modifyToken(id: Int): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val token = tokenTable.filter(_.id === id).joinLeft(personTable).on(_.ownerId === _.id)
    db.run(token.result).map {
      case result @ Seq((token: Token, Some(owner: Person))) =>
        logger.debug(s"Result -> $result")
        val form = modifyTokenForm.bind(Map(
          FormKey.tokenId       -> token.id.get.toString,
          FormKey.tokenPurpose  -> token.purpose.getOrElse(""),
          // TODO: Apply play.api.data.Mapping.transform to isActive
          FormKey.tokenIsActive -> token.isActive.toString
        ))
        Ok(modify_token(token, owner, form))
      case _ =>
        BadRequest("Oops. You tried to edit a non-existing token...")
    }
  }

  def modifyTokenPost(id: Int): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    modifyTokenForm.bindFromRequest.fold(
      formWithErrors => {
        val token = tokenTable.filter(_.id === id).joinLeft(personTable).on(_.ownerId === _.id)
        db.run(token.result).map {
          case Seq((token: Token, Some(owner: Person))) =>
            BadRequest(modify_token(token, owner, formWithErrors))
        }
      },
      modifyTokenForm => {
        val updateQuery = tokenTable
          .filter(_.id === id)
          .map(token => (token.purpose, token.isActive))
          .update((modifyTokenForm.purpose.getOrElse(""), modifyTokenForm.isActive))
        logger.debug(s"Query = ${updateQuery.statements.mkString(" | ")}")
        db.run(updateQuery).map { _ =>
          Redirect(routes.TokenController.listTokens).flashing(FlashKey.UpdatedToken -> id.toString)
        }
      }
    )
  }

  def deleteToken(id: Int, returnTo: String): EssentialAction = isAuthenticatedAsync { implicit userId => implicit request =>
    val deleteTokenQuery = tokenTable.filter(_.id === id).delete
    db.run(deleteTokenQuery).map { _ =>
      val backRoute = returnTo match {
        case "persons" => routes.PersonController.listPersons
        case _         => routes.TokenController.listTokens
      }
      Redirect(backRoute).flashing(FlashKey.DeletedToken -> id.toString)
    }
  }

}

object TokenController {
  /**
   * Data exchange object.
   *
   * @param id ID of the person a token should be assigned to.
   */
  case class FindPersonData(id: Int)
  case class AddTokenData(
    serial: Seq[Byte],
    purpose: Option[String],
    personId: Int,
    name: String
  )

  case class TokenData(
    id: Int,
    purpose: Option[String],
    isActive: Boolean
  )

  object FormKey {
    val findPersonId   = "find-person-id"
    val findPersonName = "find-person"
    val tokenId        = "token-id"
    val tokenSerial    = "token-serial"
    val tokenPurpose   = "token-purpose"
    val tokenIsActive  = "token-active"
    val tokenOwnerName = "token-owner-name"
    val tokenOwnerId   = "token-owner-id"
  }

}
