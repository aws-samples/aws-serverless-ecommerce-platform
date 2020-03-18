import * as cdk from '@aws-cdk/core';
import * as logs from '@aws-cdk/aws-logs';
import * as sam from '@aws-cdk/aws-sam';
import * as ssm from '@aws-cdk/aws-ssm';
import * as dynamodb from '@aws-cdk/aws-dynamodb';

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

    // Api Gateway
    const api = new sam.CfnApi(this, "Api", {
      endpointConfiguration: "REGIONAL",
      stageName: API_STAGE_NAME,
      tracingEnabled: true
    });
    new ssm.StringParameter(this, "ApiUrlParameter", {
      parameterName: "/ecommerce/"+env.valueAsString+"/payment-3p/api/url",
      simpleName: false,
      stringValue: "https://"+api.ref+".execute-api."+cdk.Stack.of(this).region+".amazonaws.com/"+API_STAGE_NAME
    });

    // DynamoDB table
    const table = new dynamodb.Table(this, "Table", {
      partitionKey: { name: "paymentToken", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });
    new ssm.StringParameter(this, "TableNameParameter", {
      parameterName: "/ecommerce/"+env.valueAsString+"/payment-3p/table/name",
      simpleName: false,
      stringValue: table.tableName
    });

    // Function environment variables
    const envVars = {
      TABLE_NAME: table.tableName,
      ENVIRONMENT: env.valueAsString,
      LOG_LEVEL: logLevel.valueAsString,
      POWERTOOLS_SERVICE_NAME: SERVICE_NAME,
      POWERTOOLS_TRACE_DISABLED: "false"
    };

    // Check function
    const checkFunction = new sam.CfnFunction(this, "CheckFunction", {
      codeUri: "src/check/",
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
            path: "/check",
            restApiId: api.ref
          }
        }
      },
      policies: [{
        statement: {
          Effect: "Allow",
          Action: "dynamodb:GetItem",
          Resource: table.tableArn
        }
      }]
    });
    new logs.LogGroup(this, "CheckLogGroup", {
      logGroupName: "/aws/lambda/"+checkFunction.ref,
      // TODO: fix this
      retention: 30 //retentionInDays.valueAsNumber
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
      },
      policies: [{
        statement: {
          Effect: "Allow",
          Action: "dynamodb:PutItem",
          Resource: table.tableArn
        }
      }]
    });
    new logs.LogGroup(this, "PreAuthLogGroup", {
      logGroupName: "/aws/lambda/"+preAuthFunction.ref,
      // TODO: fix this
      retention: 30 //retentionInDays.valueAsNumber
    });

    // cancelPayment function
    const cancelPaymentFunction = new sam.CfnFunction(this, "CancelPaymentFunction", {
      codeUri: "src/cancelPayment/",
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
            path: "/cancelPayment",
            restApiId: api.ref
          }
        }
      },
      policies: [{
        statement: {
          Effect: "Allow",
          Action: [
            "dynamodb:GetItem",
            "dynamodb:DeleteItem"
          ],
          Resource: table.tableArn
        }
      }]
    });
    new logs.LogGroup(this, "CancelPaymentLogGroup", {
      logGroupName: "/aws/lambda/"+cancelPaymentFunction.ref,
      // TODO: fix this
      retention: 30 //retentionInDays.valueAsNumber
    });

    // processPayment function
    const processPaymentFunction = new sam.CfnFunction(this, "ProcessPaymentFunction", {
      codeUri: "src/processPayment/",
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
            path: "/processPayment",
            restApiId: api.ref
          }
        }
      },
      policies: [{
        statement: {
          Effect: "Allow",
          Action: [
            "dynamodb:GetItem",
            "dynamodb:DeleteItem"
          ],
          Resource: table.tableArn
        }
      }]
    });
    new logs.LogGroup(this, "ProcessPaymentLogGroup", {
      logGroupName: "/aws/lambda/"+processPaymentFunction.ref,
      // TODO: fix this
      retention: 30 //retentionInDays.valueAsNumber
    });

    // updateAmountFunction function
    const updateAmountFunction = new sam.CfnFunction(this, "UpdateAmountFunction", {
      codeUri: "src/updateAmount/",
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
            path: "/updateAmount",
            restApiId: api.ref
          }
        }
      },
      policies: [{
        statement: {
          Effect: "Allow",
          Action: [
            "dynamodb:GetItem",
            "dynamodb:PutItem"
          ],
          Resource: table.tableArn
        }
      }]
    });
    new logs.LogGroup(this, "UpdateAmountLogGroup", {
      logGroupName: "/aws/lambda/"+updateAmountFunction.ref,
      // TODO: fix this
      retention: 30 //retentionInDays.valueAsNumber
    });
  }
}
