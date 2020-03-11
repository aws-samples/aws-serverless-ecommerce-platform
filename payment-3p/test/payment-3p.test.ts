import { expect as expectCDK, matchTemplate, MatchStyle } from '@aws-cdk/assert';
import * as cdk from '@aws-cdk/core';
import Payment3P = require('../lib/payment-3p-stack');

test('Empty Stack', () => {
    const app = new cdk.App();
    // WHEN
    const stack = new Payment3P.Payment3PStack(app, 'MyTestStack');
    // THEN
    expectCDK(stack).to(matchTemplate({
      "Resources": {}
    }, MatchStyle.EXACT))
});
