const AWS = require('aws-sdk');
const db = new AWS.DynamoDB.DocumentClient();
const uuidv4 = require('uuid/v4');
const TABLE_NAME = process.env.TABLE_NAME;

// Generate a response for API Gateway
function response(
        body: string | object,
        statusCode: number = 200,
        allowOrigin: string = "*",
        allowHeaders: string = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-requested-with",
        allowMethods: string = "GET,POST,PUT,DELETE,OPTIONS"
    ) {
    if (typeof body === "string") {
        body = { message: body };
    }
    return {
        statusCode: statusCode,
        body: JSON.stringify(body),
        headers: {
            "Access-Control-Allow-Headers": allowHeaders,
            "Access-Control-Allow-Origin": allowOrigin,
            "Access-Control-Allow-Methods": allowMethods
        }
    }
}

// Generate a token for the transaction
async function genToken(cardNumber: number, amount: number) : Promise<string | null> {
    var paymentToken = uuidv4();
    try {
        await db.put({
            TableName: TABLE_NAME,
            Item: {
                paymentToken: paymentToken,
                amount: amount
            }
        }).promise();
        return paymentToken;
    } catch (dbError) {
        console.log({"message": "Error storing payment token in database", "errormsg": dbError});
        return null;
    }
}

// Lambda function handler
export const handler = async (event: any = {}) : Promise <any> => {
    // Load body
    if (!event.body)
        return response("Missing body in event.", 400);
    const body = JSON.parse(event.body);
    if (!body.cardNumber)
        return response("Missing 'cardNumber' in event body.", 400);
    if (typeof body.cardNumber !== "number")
        return response("'cardNumber' is not a number.", 400);
    if (!body.amount)
        return response("Missing 'amount' in event body.", 400);
    if (typeof body.amount !== "number")
        return response("'amount' is not a number.", 400);

    // Generate the token
    var paymentToken = await genToken(body.cardNumber, body.amount);

    // Send a response
    if (paymentToken === null) {
        return response("Failed to generate a token", 500);
    } else {
        return response({"paymentToken": paymentToken});
    }
}