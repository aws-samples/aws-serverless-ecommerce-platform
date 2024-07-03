#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from '@aws-cdk/core';
import { Payment3PStack } from '../lib/payment-3p-stack';

const app = new cdk.App();
new Payment3PStack(app, 'Payment3PStack');
app.synth();