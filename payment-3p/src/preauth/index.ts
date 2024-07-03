import { DocumentClient } from 'aws-sdk/clients/dynamodb';
import { v4 as uuidv4 } from 'uuid';
const TABLE_NAME = process.env.TABLE_NAME || "TABLE_NAME";

const client = new DocumentClient();

// Generate a response for API Gateway
export function response(
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
export async function genToken(client: DocumentClient, cardNumber: string, amount: number) : Promise<string | null> {
    var paymentToken = uuidv4();
    try {
        await client.put({
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

    // Validate body
    if (!body.cardNumber)
        return response("Missing 'cardNumber' in request body.", 400);
    if (typeof body.cardNumber !== "string")
        return response("'cardNumber' is not a string.", 400);
    if (body.cardNumber.length !== 16)
        return response("'cardNumber' is not 16 characters long.", 400);
    if (!body.amount)
        return response("Missing 'amount' in request body.", 400);
    if (typeof body.amount !== "number")
        return response("'amount' is not a number.", 400);
    if (body.amount < 0)
        return response("'amount' should be a positive number.", 400)

    // Generate the token
    var paymentToken = await exports.genToken(client, body.cardNumber, body.amount);

    // Send a response
    if (paymentToken === null) {
        return response("Failed to generate a token", 500);
    } else {
        return response({"paymentToken": paymentToken});
    }
}