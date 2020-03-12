import * as cdk from '@aws-cdk/core';
import * as logs from '@aws-cdk/aws-logs';
import * as sam from '@aws-cdk/aws-sam';
import * as ssm from '@aws-cdk/aws-ssm';

const API_STAGE_NAME = "prod";
const FUNCTION_RUNTIME = "nodejs12.x";
const SERVICE_NAME = "payment-3p";

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
      POWERTOOLS_SERVICE_NAME: SERVICE_NAME,
      POWERTOOLS_TRACE_DISABLED: "false"
    };

    // Api gateway
    const api = new sam.CfnApi(this, "Api", {
      endpointConfiguration: "REGIONAL",
      stageName: API_STAGE_NAME,
      tracingEnabled: true
    });
    new ssm.StringParameter(this, "ApiUrlParameter", {
      stringValue: "https://"+api.ref+".execute-api."+cdk.Stack.of(this).region+".amazonaws.com/"+API_STAGE_NAME
    });

    // Pre Auth function
    const preAuthFunction = new sam.CfnFunction(this, "PreAuthFunction", {
      codeUri: "src/preauth/",
      handler: "index.handler",
      runtime: FUNCTION_RUNTIME,
      environment: {
        variables: envVars
      },
      events: {
        Api: {
          type: "Api",
          properties: {
            method: "POST",
            path: "/preauth",
            restApiId: api.ref
          }
        }
      }
    });
    new logs.LogGroup(this, "PreAuthLogGroup", {
      logGroupName: "/aws/lambda/"+preAuthFunction.functionName,
      // TODO: fix this
      retention: 30 //retentionInDays.valueAsNumber
    });
  }
}
