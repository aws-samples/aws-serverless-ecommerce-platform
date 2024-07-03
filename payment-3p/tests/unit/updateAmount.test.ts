const AWS = require('aws-sdk');
const AWSMock = require('aws-sdk-mock');
import { GetItemInput, PutItemInput } from "aws-sdk/clients/dynamodb";
const fn = require('../../src/updateAmount');

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

test('updateAmount', async () => {
    AWSMock.mock("DynamoDB.DocumentClient", "get", (params: GetItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(null, {
            Item: {
                paymentToken: "TOKEN",
                amount: 3000
            }
        });
    });
    AWSMock.mock("DynamoDB.DocumentClient", "put", (params: PutItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Item.paymentToken).toBe("TOKEN");
        expect(params.Item.amount).toBe(2000);
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.updateAmount(client, "TOKEN", 2000);
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(true);
});

test('updateAmount with exceeding amount', async () => {
    AWSMock.mock("DynamoDB.DocumentClient", "get", (params: GetItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(null, {
            Item: {
                paymentToken: "TOKEN",
                amount: 3000
            }
        });
    });
    AWSMock.mock("DynamoDB.DocumentClient", "put", (params: PutItemInput, callback: Function) => {
        expect(params).toBe(undefined);
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.updateAmount(client, "TOKEN", 4000);
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(false);
});

test('updateAmount with no item', async () => {
    AWSMock.mock("DynamoDB.DocumentClient", "get", (params: GetItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(null, {});
    });
    AWSMock.mock("DynamoDB.DocumentClient", "put", (params: PutItemInput, callback: Function) => {
        expect(params).toBe(undefined);
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.updateAmount(client, "TOKEN", 3000);
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(false);
});

test('updateAmount with DynamoDB get error', async () => {
    AWSMock.mock("DynamoDB.DocumentClient", "get", (params: GetItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(new Error(), null);
    });
    AWSMock.mock("DynamoDB.DocumentClient", "put", (params: PutItemInput, callback: Function) => {
        expect(params).toBe(undefined);
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.updateAmount(client, "TOKEN", 2000);
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(null);
});

test('updateAmount with DynamoDB put error', async () => {
    AWSMock.mock("DynamoDB.DocumentClient", "get", (params: GetItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(null, {
            Item: {
                paymentToken: "TOKEN",
                amount: 3000
            }
        });
    });
    AWSMock.mock("DynamoDB.DocumentClient", "put", (params: PutItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Item.paymentToken).toBe("TOKEN");
        expect(params.Item.amount).toBe(2000);
        callback(new Error(), null);
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.updateAmount(client, "TOKEN", 2000);
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(null);
});

test('handler', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
            "paymentToken": "TOKEN",
            amount: 3000
        })
    };
    const response = await fn.handler(event, {});

    expect(response.statusCode).toBe(200);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(body.ok).toBe(true);

    fn.updateAmount = updateAmount;
});

test('handler with failing check', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(false));

    const event = {
        body: JSON.stringify({
            "paymentToken": "TOKEN",
            amount: 3000
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.updateAmount).toBeCalled();
    expect(response.statusCode).toBe(200);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(body.ok).toBe(false);

    fn.updateAmount = updateAmount;
});

test('handler with missing body', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(true));

    const event = {
    };
    const response = await fn.handler(event, {});

    expect(fn.updateAmount).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");

    fn.updateAmount = updateAmount;
});

test('handler with missing paymentToken', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
            amount: 3000
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.updateAmount).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("paymentToken")

    fn.updateAmount = updateAmount;
});

test('handler with wrong paymentToken type', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
            paymentToken: 3000,
            amount: 3000
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.updateAmount).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("paymentToken")

    fn.updateAmount = updateAmount;
});

test('handler with missing amount', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
            paymentToken: "TOKEN"
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.updateAmount).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("amount")

    fn.updateAmount = updateAmount;
});

test('handler with wrong amount type', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
            paymentToken: "TOKEN",
            amount: "3000"
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.updateAmount).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("amount")

    fn.updateAmount = updateAmount;
});

test('handler with negative amount', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
            paymentToken: "TOKEN",
            amount: -3000
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.updateAmount).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("amount")

    fn.updateAmount = updateAmount;
});

test('handler with updateAmount failure', async () => {
    const updateAmount = fn.updateAmount;
    fn.updateAmount = jest.fn();
    fn.updateAmount.mockReturnValue(Promise.resolve(null));

    const event = {
        body: JSON.stringify({
            paymentToken: "TOKEN",
            amount: 3000
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.updateAmount).toBeCalled();
    expect(response.statusCode).toBe(500);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");

    fn.updateAmount = updateAmount;
});