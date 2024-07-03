const AWS = require('aws-sdk');
const axios = require('axios');
import { v4 as uuidv4 } from 'uuid';
const env = process.env.ENVIRONMENT || "dev";

test('processPayment', async () => {
    const ssm = new AWS.SSM();
    const dynamodb = new AWS.DynamoDB.DocumentClient();

    const apiUrl = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/api/url"
    }).promise()).Parameter.Value;
    const tableName = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/table/name"
    }).promise()).Parameter.Value;

    const item = {
        paymentToken: uuidv4(),
        amount: 3000
    };

    await dynamodb.put({
        TableName: tableName,
        Item: item
    }).promise();

    await axios.post(apiUrl+"/processPayment", {
        paymentToken: item.paymentToken
    }).then((response: any) => {
        expect(response.status).toBe(200);
        expect(typeof response.data.ok).toBe("boolean");
        expect(response.data.ok).toBe(true);
    }, (error : any) => {
        expect(error).toBe(undefined);
    });

    const ddbResponse = await dynamodb.get({
        TableName: tableName,
        Key: { paymentToken: item.paymentToken }
    }).promise();
    expect(ddbResponse.Item).toBe(undefined);
});

test('processPayment without item', async () => {
    const ssm = new AWS.SSM();
    const dynamodb = new AWS.DynamoDB.DocumentClient();

    const apiUrl = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/api/url"
    }).promise()).Parameter.Value;
    const tableName = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/table/name"
    }).promise()).Parameter.Value;

    await axios.post(apiUrl+"/processPayment", {
        paymentToken: "TOKEN"
    }).then((response: any) => {
        expect(response.status).toBe(200);
        expect(typeof response.data.ok).toBe("boolean");
        expect(response.data.ok).toBe(false);
    }, (error : any) => {
        expect(error).toBe(undefined);
    });
});

test('processPayment without paymentToken', async () => {
    const ssm = new AWS.SSM();
    const dynamodb = new AWS.DynamoDB.DocumentClient();

    const apiUrl = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/api/url"
    }).promise()).Parameter.Value;
    const tableName = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/table/name"
    }).promise()).Parameter.Value;

    await axios.post(apiUrl+"/processPayment", {
    }).then((response: any) => {
        expect(response).toBe(undefined);
    }, (error : any) => {
        expect(error.response.status).toBe(400);
        expect(typeof error.response.data.message).toBe("string");
        expect(error.response.data.message).toContain("paymentToken");
    });
});