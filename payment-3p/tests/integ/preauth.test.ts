const AWS = require('aws-sdk');
const axios = require('axios');
const env = process.env.ENVIRONMENT || "dev";

test('preauth', async () => {
    const ssm = new AWS.SSM();
    const dynamodb = new AWS.DynamoDB.DocumentClient();

    const apiUrl = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/api/url"
    }).promise()).Parameter.Value;
    const tableName = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/table/name"
    }).promise()).Parameter.Value;

    const response = await axios.post(apiUrl+"/preauth", {
        cardNumber: "1234567890123456",
        amount: 30000
    });
    expect(response.status).toBe(200);
    expect(typeof response.data.paymentToken).toBe("string");
    expect(response.data.message).toBe(undefined);

    const paymentToken = response.data.paymentToken;
    const ddbResponse = await dynamodb.get({
        TableName: tableName,
        Key: { paymentToken }
    }).promise();

    expect(ddbResponse.Item).not.toBe(undefined);
    expect(ddbResponse.Item.paymentToken).toBe(paymentToken);
    expect(ddbResponse.Item.amount).toBe(30000);

    await dynamodb.delete({
        TableName: tableName,
        Key: { paymentToken }
    }).promise();
});

test('preauth without cardNumber', async () => {
    const ssm = new AWS.SSM();
    const dynamodb = new AWS.DynamoDB.DocumentClient();

    const apiUrl = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/api/url"
    }).promise()).Parameter.Value;
    const tableName = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/table/name"
    }).promise()).Parameter.Value;

    await axios.post(apiUrl+"/preauth", {
        amount: 30000
    }).then((response: any) => {
        expect(response).toBe(undefined);
    }, (error : any) => {
        expect(error.response.status).toBe(400);
        expect(typeof error.response.data.message).toBe("string");
        expect(error.response.data.message).toContain("cardNumber");
    });
});

test('preauth without amount', async () => {
    const ssm = new AWS.SSM();
    const dynamodb =  new AWS.DynamoDB.DocumentClient();

    const apiUrl = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/api/url"
    }).promise()).Parameter.Value;
    const tableName = (await ssm.getParameter({
        Name: "/ecommerce/"+env+"/payment-3p/table/name"
    }).promise()).Parameter.Value;

    await axios.post(apiUrl+"/preauth", {
        cardNumber: "1234567890123456"
    }).then((response: any) => {
        expect(response).toBe(undefined);
    }, (error : any) => {
        expect(error.response.status).toBe(400);
        expect(typeof error.response.data.message).toBe("string");
        expect(error.response.data.message).toContain("amount");
    });
});