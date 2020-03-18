const AWS = require('aws-sdk');
const AWSMock = require('aws-sdk-mock');
import { DeleteItemInput, GetItemInput } from "aws-sdk/clients/dynamodb";
const fn = require('../../src/cancelPayment');

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

test('cancelPayment', async () => {
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
    AWSMock.mock("DynamoDB.DocumentClient", "delete", (params: DeleteItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.cancelPayment(client, "TOKEN");
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(true);
});

test('cancelPayment without item', async () => {
    AWSMock.mock("DynamoDB.DocumentClient", "get", (params: GetItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(null, {});
    });
    AWSMock.mock("DynamoDB.DocumentClient", "delete", (params: DeleteItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.cancelPayment(client, "TOKEN");
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(false);
});

test('cancelPayment with DynamoDB get error', async () => {
    AWSMock.mock("DynamoDB.DocumentClient", "get", (params: GetItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(new Error(), null);
    });
    AWSMock.mock("DynamoDB.DocumentClient", "delete", (params: DeleteItemInput, callback: Function) => {
        expect(params).toBe(undefined);
        callback(null, {});
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.cancelPayment(client, "TOKEN");
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(null);
});

test('cancelPayment with DynamoDB delete error', async () => {
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
    AWSMock.mock("DynamoDB.DocumentClient", "delete", (params: DeleteItemInput, callback: Function) => {
        expect(params.TableName).toBe("TABLE_NAME");
        expect(params.Key.paymentToken).toBe("TOKEN");
        callback(new Error(), null);
    });
    const client = new AWS.DynamoDB.DocumentClient();

    const retval = await fn.cancelPayment(client, "TOKEN", 2000);
    AWSMock.restore("DynamoDB.DocumentClient");

    expect(retval).toBe(null);
});

test('handler', async () => {
    const cancelPayment = fn.cancelPayment;
    fn.cancelPayment = jest.fn();
    fn.cancelPayment.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
            "paymentToken": "TOKEN"
        })
    };
    const response = await fn.handler(event, {});

    expect(response.statusCode).toBe(200);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(body.ok).toBe(true);

    fn.cancelPayment = cancelPayment;
});

test('handler with failing cancellation', async () => {
    const cancelPayment = fn.cancelPayment;
    fn.cancelPayment = jest.fn();
    fn.cancelPayment.mockReturnValue(Promise.resolve(false));

    const event = {
        body: JSON.stringify({
            "paymentToken": "TOKEN"
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.cancelPayment).toBeCalled();
    expect(response.statusCode).toBe(200);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(body.ok).toBe(false);

    fn.cancelPayment = cancelPayment;
});

test('handler with missing body', async () => {
    const cancelPayment = fn.cancelPayment;
    fn.cancelPayment = jest.fn();
    fn.cancelPayment.mockReturnValue(Promise.resolve(true));

    const event = {
    };
    const response = await fn.handler(event, {});

    expect(fn.cancelPayment).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");

    fn.cancelPayment = cancelPayment;
});

test('handler with missing paymentToken', async () => {
    const cancelPayment = fn.cancelPayment;
    fn.cancelPayment = jest.fn();
    fn.cancelPayment.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.cancelPayment).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("paymentToken")

    fn.cancelPayment = cancelPayment;
});

test('handler with wrong paymentToken type', async () => {
    const cancelPayment = fn.cancelPayment;
    fn.cancelPayment = jest.fn();
    fn.cancelPayment.mockReturnValue(Promise.resolve(true));

    const event = {
        body: JSON.stringify({
            paymentToken: 3000
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.cancelPayment).not.toBeCalled();
    expect(response.statusCode).toBe(400);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");
    expect(body.message).toContain("paymentToken")

    fn.cancelPayment = cancelPayment;
});

test('handler with cancelPayment failure', async () => {
    const cancelPayment = fn.cancelPayment;
    fn.cancelPayment = jest.fn();
    fn.cancelPayment.mockReturnValue(Promise.resolve(null));

    const event = {
        body: JSON.stringify({
            paymentToken: "TOKEN"
        })
    };
    const response = await fn.handler(event, {});

    expect(fn.cancelPayment).toBeCalled();
    expect(response.statusCode).toBe(500);
    expect(response.body).not.toBe(undefined);
    const body = JSON.parse(response.body);
    expect(typeof body.message).toBe("string");

    fn.cancelPayment = cancelPayment;
});