package modules

import java.util

import io.swagger.core.filter.SwaggerSpecFilter
import io.swagger.model.ApiDescription
import io.swagger.models.Model
import io.swagger.models.Operation
import io.swagger.models.parameters.Parameter
import io.swagger.models.properties.Property
import play.api.Logger

// see https://www.cakesolutions.net/teamblogs/swagger-with-play-all-you-need-to-know
// TODO: Currently not used
class SwaggerConfigurationFilter extends SwaggerSpecFilter {
  override def isOperationAllowed(
    operation: Operation,
    api: ApiDescription,
    params: util.Map[String, util.List[String]],
    cookies: util.Map[String, String],
    headers: util.Map[String, util.List[String]]
  ): Boolean = true

  override def isParamAllowed(
    parameter: Parameter,
    operation: Operation,
    api: ApiDescription,
    params: util.Map[String, util.List[String]],
    cookies: util.Map[String, String],
    headers: util.Map[String, util.List[String]]
  ): Boolean = true

  override def isPropertyAllowed(
    model: Model,
    property: Property,
    propertyName: String,
    params: util.Map[String, util.List[String]],
    cookies: util.Map[String, String],
    headers: util.Map[String, util.List[String]]
  ): Boolean = {
    Logger.debug(s"Model = ${model.getTitle}")
    Logger.debug(s"Property = $property")
    true
  }
}
