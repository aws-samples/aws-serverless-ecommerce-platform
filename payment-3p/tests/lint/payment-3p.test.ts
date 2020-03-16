import { expect as expectCDK, haveResourceLike } from '@aws-cdk/assert';
import * as cdk from '@aws-cdk/core';
import Payment3P = require('../../lib/payment-3p-stack');

// TODO:
// - Test parameters
// - Test if Lambda functions have a corresponding LogGroup

test("Has Api", () => {
  const app = new cdk.App();
  const stack = new Payment3P.Payment3PStack(app, "MyTestStack");

  expectCDK(stack).to(haveResourceLike("AWS::Serverless::Api"));
});

test("Has Functions", () => {
  const app = new cdk.App();
  const stack = new Payment3P.Payment3PStack(app, "MyTestStack");

  expectCDK(stack).to(haveResourceLike("AWS::Serverless::Function", {
    "CodeUri": "src/check/"
  }));
  expectCDK(stack).to(haveResourceLike("AWS::Serverless::Function", {
    "CodeUri": "src/preauth/"
  }));
  expectCDK(stack).to(haveResourceLike("AWS::Serverless::Function", {
    "CodeUri": "src/processPayment/"
  }));
  expectCDK(stack).to(haveResourceLike("AWS::Serverless::Function", {
    "CodeUri": "src/updateAmount/"
  }));
});

test("Has Table", () => {
  const app = new cdk.App();
  const stack = new Payment3P.Payment3PStack(app, "MyTestStack");

  expectCDK(stack).to(haveResourceLike("AWS::DynamoDB::Table", {}));
});