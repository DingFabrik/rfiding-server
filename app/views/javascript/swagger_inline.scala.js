@() {
window.onload = function() {

      // Build a system
      const ui = SwaggerUIBundle({
        //url: "https://petstore.swagger.io/v2/swagger.json",
        url: "@controllers.routes.ApiHelpController.getResources",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout"
      })

      window.ui = ui
    }
}
