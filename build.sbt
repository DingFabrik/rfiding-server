name := "rfiding-server"

organization := "de.dingfabrik.rfiding"

version := "1.0-SNAPSHOT"

lazy val root = (project in file(".")).enablePlugins(PlayScala)

scalaVersion := "2.12.4"

libraryDependencies ++= Seq(
  guice,
  "org.specs2"             %% "specs2-core"          % "4.3.4" % "test",
  "org.scalatestplus.play" %% "scalatestplus-play"    % "3.1.2" % Test,
  // Slick, Evolutions & SQLite
  "com.typesafe.play"      %% "play-slick"            % "3.0.1",
  "com.typesafe.play"      %% "play-slick-evolutions" % "3.0.1",
  "org.xerial"             %  "sqlite-jdbc"           % "3.21.0",
  // Webjars
  "org.webjars"            %% "webjars-play"          % "2.6.3",
  "org.webjars"            %  "bootstrap"             % "4.1.3",
  "org.webjars"            %  "jquery-ui"             % "1.12.1",
  "org.webjars.npm"        %  "feather-icons"         % "4.7.3",
  "org.webjars"            %  "chartjs"               % "2.7.2",
  "org.webjars"            %  "highlightjs"           % "9.8.0",

  // Secure password hashing
  "de.mkammerer"           %  "argon2-jvm"           % "2.4",

  // Slick code gen. Do we really want that?
  //"com.typesafe.slick" %% "slick-codegen" % "3.2.0"

  // Swagger REST API documentation:
  "io.swagger"             %% "swagger-play2"        % "1.6.0",
  "org.webjars"            %  "swagger-ui"           % "3.19.0",
)

// Adds additional packages into Twirl
//TwirlKeys.templateImports += "de.dingfabrik.rfiding.controllers._"

// Adds additional packages into conf/routes
// play.sbt.routes.RoutesKeys.routesImport += "de.dingfabrik.rfiding.binders._"
