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
    AWSMock.mock("DynamoDB.DocumentClient", "put", (params: PutItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Item.amount).toBe(200);
        expect(typeof params.Item.paymentToken).toBe("string");
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.genToken(client, "1234567890123456", 200);
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).not.toBe(null);
    expect(typeof retval).toBe("string");
});

test('genToken with DynamoDB error', async () => {
    AWSMock.mock("DynamoDB.DocumentClient", "put", (params: PutItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Item.amount).toBe(200);
        expect(typeof params.Item.paymentToken).toBe("string");
        callback(new Error(), null);
    });
    const client = new AWS.DynamoDB.DocumentClient();
    const retval = await fn.genToken(client, "1234567890123456", 200);
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(null);
});

test('handler', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve("TOKEN"));

    const event = {
        body: JSON.stringify({
            cardNumber: "1234567890123456",
            amount: 200
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).toBeCalled();
    expect(response.statusCode).toBe(200);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(body.paymentToken).toBe("TOKEN");

    fn.genToken = genToken;
});

test('handler with missing body', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve("TOKEN"));

    const event = {
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");

    fn.genToken = genToken;
});

test('handler with missing cardNumber', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve("TOKEN"));

    const event = {
        body: JSON.stringify({
            amount: 200
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("cardNumber");

    fn.genToken = genToken;
});

test('handler with wrong cardNumber type', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve("TOKEN"));

    const event = {
        body: JSON.stringify({
            cardNumber: 1234567890123456,
            amount: 200
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("cardNumber");

    fn.genToken = genToken;
});

test('handler with cardNumber too short', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve("TOKEN"));

    const event = {
        body: JSON.stringify({
            cardNumber: "123456789012345",
            amount: 200
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("cardNumber");

    fn.genToken = genToken;
});

test('handler with missing amount', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve("TOKEN"));

    const event = {
        body: JSON.stringify({
            cardNumber: "1234567890123456"
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("amount");

    fn.genToken = genToken;
});

test('handler with wrong amount type', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve("TOKEN"));

    const event = {
        body: JSON.stringify({
            cardNumber: "1234567890123456",
            amount: "200"
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("amount");

    fn.genToken = genToken;
});

test('handler with negative amount', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve("TOKEN"));

    const event = {
        body: JSON.stringify({
            cardNumber: "1234567890123456",
            amount: -200
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("amount");

    fn.genToken = genToken;
});

test('handler with genToken error', async () => {
    const genToken = fn.genToken;
    fn.genToken = jest.fn();
    fn.genToken.mockReturnValue(Promise.resolve(null));

    const event = {
        body: JSON.stringify({
            cardNumber: "1234567890123456",
            amount: 200
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.genToken).toBeCalled();
    expect(response.statusCode).toBe(500);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("token");

    fn.genToken = genToken;
});