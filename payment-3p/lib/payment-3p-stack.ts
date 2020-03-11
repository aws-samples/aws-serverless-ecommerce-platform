import * as cdk from '@aws-cdk/core';
import * as apigw from '@aws-cdk/aws-apigateway';
import * as lambda_ from '@aws-cdk/aws-lambda';
import * as logs from '@aws-cdk/aws-logs';
import * as ssm from '@aws-cdk/aws-ssm';

export class Payment3PStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Parameters
    const env = new cdk.CfnParameter(this, "Environment", { default: "dev", type: "String" });
    const logLevel = new cdk.CfnParameter(this, "LogLevel", { default: "INFO", type: "String" });
    const retentionInDays = new cdk.CfnParameter(this, "RetentionInDays", { default: 30, type: "Number" });

    // Function environment variables
    const envVars = {
      ENVIRONMENT: env.valueAsString,
      LOG_LEVEL: logLevel.valueAsString,
      POWERTOOLS_SERVICE_NAME: "payment-3p",
      POWERTOOLS_TRACE_DISABLED: "false"
    };

    // Api gateway
    const api = new apigw.RestApi(this, "Api", {
      deployOptions: {
        stageName: "prod",
        tracingEnabled: true
      }, 
      endpointConfiguration: {
        types: [ apigw.EndpointType.REGIONAL ]
      }
    });
    new ssm.StringParameter(this, "ApiUrlParameter", {
      stringValue: "https://"+api.restApiId+".execute-api."+cdk.Stack.of(this).region+".amazonaws.com/prod"
    });

    // Pre Auth function
    const preAuthFunction = new lambda_.Function(this, "PreAuthFunction", {
      code: lambda_.Code.fromAsset("src/preauth/"),
      handler: "index.handler",
      runtime: lambda_.Runtime.NODEJS_12_X,
      environment: envVars
    });
    new apigw.Method(this, "PreAuthMethod", {
      httpMethod: "POST",
      resource: new apigw.Resource(this, "PreAuthResource", {
        parent: api.root,
        pathPart: "preauth",
        defaultCorsPreflightOptions: {
          allowOrigins: ["*"],
          allowMethods: ["POST"]
        }
      }),
      integration: new apigw.LambdaIntegration(preAuthFunction)
    });
    new logs.LogGroup(this, "PreAuthLogGroup", {
      logGroupName: "/aws/lambda/"+preAuthFunction.functionName
    });
  }
}
