const AWS = require('aws-sdk');
const AWSMock = require('aws-sdk-mock');
import { PutItemInput } from "aws-sdk/clients/dynamodb";
const fn = require('../../src/preauth');

test('response', () => {
    const retval = fn.response("MESSAGE", 400, "ALLOW_ORIGIN", "ALLOW_HEADERS", "ALLOW_METHODS");
    expect(typeof retval.body).toBe("string");
    const body = JSON.parse(retval.body);
    expect(body).toEqual({
        "message": "MESSAGE"
    });
    expect(retval.statusCode).toBe(400);
    expect(retval.headers).toEqual({
        "Access-Control-Allow-Headers": "ALLOW_HEADERS",
        "Access-Control-Allow-Origin": "ALLOW_ORIGIN",
        "Access-Control-Allow-Methods": "ALLOW_METHODS"
    });
});

test('genToken', async () => {
    AWSMock.setSDKInstance(AWS);
    AWSMock.mock("DynamoDB.DocumentClient", "put", (params: PutItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Item.amount).toBe(200);
        expect(typeof params.Item.paymentToken).toBe("string");
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.genToken(client, "1234567890123456", 200);
    expect(retval).not.toBe(null);
    expect(typeof retval).toBe("string");
});